# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
SEC EDGAR Connector

Handles fetching regulatory content from SEC EDGAR system,
including RSS feeds and the SEC API.
"""

import frappe
from frappe import _
from frappe.utils import getdate

from .base_connector import BaseConnector


class SECEdgarConnector(BaseConnector):
	"""
	Connector for SEC EDGAR RSS feeds and API.

	Fetches press releases, rule changes, and other regulatory
	content from the Securities and Exchange Commission.
	"""

	# SEC RSS Feed URLs
	SEC_FEEDS = {
		"press_releases": "https://www.sec.gov/news/pressreleases.rss",
		"final_rules": "https://www.sec.gov/rules/final.rss",
		"proposed_rules": "https://www.sec.gov/rules/proposed.rss",
		"interpretive": "https://www.sec.gov/rules/interp.rss",
		"other_releases": "https://www.sec.gov/rules/other.rss",
	}

	def fetch_updates(self):
		"""
		Fetch SEC filings and releases.

		Returns:
			list: List of parsed update dicts
		"""
		updates = []

		# If specific URL provided, use that
		if self.url and "sec.gov" in self.url:
			updates.extend(self._fetch_rss_feed(self.url))
		else:
			# Fetch from all SEC feeds
			for feed_name, feed_url in self.SEC_FEEDS.items():
				try:
					feed_updates = self._fetch_rss_feed(feed_url)
					updates.extend(feed_updates)
				except Exception as e:
					frappe.log_error(
						message=f"Error fetching {feed_name}: {str(e)}", title=_("SEC Feed Error")
					)

		return updates

	def _fetch_rss_feed(self, url):
		"""
		Fetch and parse a single RSS feed.

		Args:
			url: RSS feed URL

		Returns:
			list: List of parsed updates
		"""
		try:
			import feedparser
		except ImportError:
			frappe.throw(
				_("feedparser package is required. " "Please install it with: pip install feedparser")
			)

		try:
			feed = feedparser.parse(url, agent=self.user_agent)
		except Exception as e:
			self._log_error(_("Failed to fetch SEC feed"), e)
			return []

		if feed.bozo and not feed.entries:
			return []

		updates = []
		for entry in feed.entries:
			parsed = self.parse_item(entry)
			if parsed:
				# Apply filters
				title = parsed.get("title", "")
				if self._filter_by_keywords(title):
					doc_type = parsed.get("document_type", "")
					if self._filter_by_document_types(doc_type):
						updates.append(parsed)

		return updates

	def parse_item(self, item):
		"""
		Parse SEC RSS entry.

		Args:
			item: feedparser entry object

		Returns:
			dict: Parsed update data or None
		"""
		# Extract publication date
		pub_date = self._extract_date(item)

		# Skip if older than last sync
		if self.last_sync and pub_date:
			if pub_date < getdate(self.last_sync):
				return None

		# Determine document type from title/category
		doc_type = self._classify_document_type(item.get("title", ""))

		# Extract content
		summary = item.get("summary", "")[:2000]

		return {
			"title": item.get("title", "")[:255],
			"publication_date": pub_date,
			"summary": summary,
			"full_text": summary,  # RSS only has summary
			"original_url": item.get("link", ""),
			"regulatory_body": "SEC",
			"document_type": doc_type,
		}

	def _extract_date(self, item):
		"""
		Extract publication date from RSS entry.

		Args:
			item: feedparser entry object

		Returns:
			date: Publication date or None
		"""
		if hasattr(item, "published_parsed") and item.published_parsed:
			try:
				return getdate(
					f"{item.published_parsed.tm_year}-"
					f"{item.published_parsed.tm_mon:02d}-"
					f"{item.published_parsed.tm_mday:02d}"
				)
			except Exception as e:
				frappe.log_error(
					message=f"Failed to parse published date from SEC EDGAR feed: {str(e)}",
					title="SEC EDGAR Date Parse Error",
				)

		if hasattr(item, "updated_parsed") and item.updated_parsed:
			try:
				return getdate(
					f"{item.updated_parsed.tm_year}-"
					f"{item.updated_parsed.tm_mon:02d}-"
					f"{item.updated_parsed.tm_mday:02d}"
				)
			except Exception as e:
				frappe.log_error(
					message=f"Failed to parse updated date from SEC EDGAR feed: {str(e)}",
					title="SEC EDGAR Date Parse Error",
				)

		return None

	def _classify_document_type(self, title):
		"""
		Classify SEC document type from title.

		Args:
			title: Document title

		Returns:
			str: Document type
		"""
		title_lower = title.lower()

		if "final rule" in title_lower:
			return "Rule"
		elif "proposed rule" in title_lower:
			return "Proposed Rule"
		elif "interpretive" in title_lower:
			return "Interpretation"
		elif "guidance" in title_lower:
			return "Guidance"
		elif "amendment" in title_lower:
			return "Amendment"
		elif "no-action" in title_lower:
			return "Guidance"
		elif "enforcement" in title_lower or "charges" in title_lower:
			return "Enforcement"
		elif "staff" in title_lower:
			return "Staff Bulletin"
		else:
			return "Release"

	def fetch_full_document(self, url):
		"""
		Fetch full document content from SEC website.

		Args:
			url: Document URL

		Returns:
			str: Full document text
		"""
		try:
			import requests
			from bs4 import BeautifulSoup
		except ImportError:
			return ""

		try:
			headers = {"User-Agent": self.user_agent}
			response = requests.get(url, headers=headers, timeout=30)
			response.raise_for_status()

			soup = BeautifulSoup(response.text, "html.parser")

			# Find main content area
			content = soup.find("div", {"class": "article-body"})
			if not content:
				content = soup.find("div", {"id": "content"})
			if not content:
				content = soup.find("main")
			if not content:
				content = soup.body

			if content:
				# Remove script and style elements
				for element in content(["script", "style", "nav", "footer"]):
					element.decompose()
				return content.get_text(separator=" ", strip=True)

		except Exception as e:
			frappe.log_error(
				message=f"Error fetching full document: {str(e)}", title=_("SEC Document Fetch Error")
			)

		return ""
