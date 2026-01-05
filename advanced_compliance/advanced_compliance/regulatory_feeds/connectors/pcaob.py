# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
PCAOB Connector

Handles fetching regulatory content from PCAOB
(Public Company Accounting Oversight Board).
"""

import frappe
from frappe import _
from frappe.utils import getdate

from .base_connector import BaseConnector


class PCAOBConnector(BaseConnector):
	"""
	Connector for PCAOB RSS feeds.

	Fetches auditing standards, rules, and guidance from PCAOB.
	"""

	# PCAOB RSS Feeds
	PCAOB_FEEDS = {
		"news": "https://pcaobus.org/news-events/news-releases/rss",
		"rulemaking": "https://pcaobus.org/oversight/standards/rulemaking-dockets/rss",
	}

	def fetch_updates(self):
		"""
		Fetch PCAOB releases.

		Returns:
			list: List of parsed update dicts
		"""
		updates = []

		# If specific URL provided, use that
		if self.url:
			updates.extend(self._fetch_rss_feed(self.url))
		else:
			# Fetch from all PCAOB feeds
			for feed_name, feed_url in self.PCAOB_FEEDS.items():
				try:
					feed_updates = self._fetch_rss_feed(feed_url)
					updates.extend(feed_updates)
				except Exception as e:
					frappe.log_error(
						message=f"Error fetching {feed_name}: {str(e)}", title=_("PCAOB Feed Error")
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
			self._log_error(_("Failed to fetch PCAOB feed"), e)
			return []

		if feed.bozo and not feed.entries:
			return []

		updates = []
		for entry in feed.entries:
			parsed = self.parse_item(entry)
			if parsed:
				title = parsed.get("title", "")
				if self._filter_by_keywords(title):
					doc_type = parsed.get("document_type", "")
					if self._filter_by_document_types(doc_type):
						updates.append(parsed)

		return updates

	def parse_item(self, item):
		"""
		Parse PCAOB RSS entry.

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

		# Determine document type
		doc_type = self._classify_document_type(item.get("title", ""))

		# Extract content
		summary = item.get("summary", "")[:2000]

		return {
			"title": item.get("title", "")[:255],
			"publication_date": pub_date,
			"summary": summary,
			"full_text": summary,
			"original_url": item.get("link", ""),
			"regulatory_body": "PCAOB",
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
			except Exception:
				pass

		return None

	def _classify_document_type(self, title):
		"""
		Classify PCAOB document type from title.

		Args:
			title: Document title

		Returns:
			str: Document type
		"""
		title_lower = title.lower()

		if "auditing standard" in title_lower or "AS " in title:
			return "Rule"
		elif "proposed" in title_lower:
			return "Proposed Rule"
		elif "guidance" in title_lower or "staff" in title_lower:
			return "Guidance"
		elif "inspection" in title_lower:
			return "Enforcement"
		elif "release" in title_lower:
			return "Release"
		else:
			return "Other"
