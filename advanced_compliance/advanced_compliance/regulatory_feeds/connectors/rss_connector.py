# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
RSS Connector

Handles fetching and parsing of RSS/Atom feeds from regulatory sources.
"""

import frappe
from frappe import _
from frappe.utils import getdate

from .base_connector import BaseConnector


class RSSConnector(BaseConnector):
	"""
	Connector for RSS/Atom feeds.

	Uses feedparser library to handle various RSS and Atom formats,
	including malformed feeds.
	"""

	def fetch_updates(self):
		"""
		Fetch and parse RSS feed.

		Returns:
			list: List of parsed update dicts
		"""
		try:
			import feedparser
		except ImportError:
			frappe.throw(
				_(
					"feedparser package is required for RSS feeds. "
					"Please install it with: pip install feedparser"
				)
			)

		try:
			feed = feedparser.parse(self.url, agent=self.user_agent)
		except Exception as e:
			self._log_error(_("Failed to fetch RSS feed"), e)
			return []

		# Check for feed errors
		if feed.bozo:
			# Feed had errors but may still have entries
			if not feed.entries:
				self._log_error(_("RSS parse error: {0}").format(feed.bozo_exception))
				return []
			# Log warning but continue processing
			frappe.log_error(
				message=f"RSS feed warning: {feed.bozo_exception}",
				title=_("Feed Warning: {0}").format(self.feed_source.source_name),
			)

		updates = []
		for entry in feed.entries:
			parsed = self.parse_item(entry)
			if parsed:
				# Apply filters
				title = parsed.get("title", "")
				summary = parsed.get("summary", "")
				combined_text = f"{title} {summary}"

				if self._filter_by_keywords(combined_text):
					doc_type = parsed.get("document_type", "")
					if self._filter_by_document_types(doc_type):
						updates.append(parsed)

		return updates

	def parse_item(self, item):
		"""
		Parse RSS entry to update data.

		Args:
			item: feedparser entry object

		Returns:
			dict: Parsed update data or None if should skip
		"""
		# Extract publication date
		pub_date = self._extract_date(item)

		# Skip if older than last sync
		if self.last_sync and pub_date:
			if pub_date < getdate(self.last_sync):
				return None

		# Extract content
		full_text = self._extract_content(item)
		summary = self._extract_summary(item, full_text)

		# Classify document type from title/category
		doc_type = self._classify_document_type(item)

		return {
			"title": item.get("title", "")[:255],
			"publication_date": pub_date,
			"summary": summary[:2000] if summary else "",
			"full_text": full_text,
			"original_url": item.get("link", ""),
			"document_type": doc_type,
			"regulatory_body": self.feed_source.regulatory_body,
		}

	def _extract_date(self, item):
		"""
		Extract publication date from RSS entry.

		Args:
			item: feedparser entry object

		Returns:
			date: Publication date or None
		"""
		# Try published_parsed first
		if hasattr(item, "published_parsed") and item.published_parsed:
			try:
				return getdate(
					f"{item.published_parsed.tm_year}-"
					f"{item.published_parsed.tm_mon:02d}-"
					f"{item.published_parsed.tm_mday:02d}"
				)
			except Exception:
				pass

		# Try updated_parsed
		if hasattr(item, "updated_parsed") and item.updated_parsed:
			try:
				return getdate(
					f"{item.updated_parsed.tm_year}-"
					f"{item.updated_parsed.tm_mon:02d}-"
					f"{item.updated_parsed.tm_mday:02d}"
				)
			except Exception:
				pass

		# Try parsing date strings
		for date_field in ["published", "updated", "date"]:
			date_str = item.get(date_field)
			if date_str:
				try:
					import dateparser

					parsed = dateparser.parse(date_str)
					if parsed:
						return getdate(parsed)
				except Exception:
					pass

		return None

	def _extract_content(self, item):
		"""
		Extract full content from RSS entry.

		Args:
			item: feedparser entry object

		Returns:
			str: Full text content
		"""
		# Try content field (Atom feeds)
		if item.get("content"):
			contents = item.get("content", [])
			if contents and isinstance(contents, list):
				# Prefer HTML content
				for content in contents:
					if content.get("type") == "text/html":
						return self._clean_html(content.get("value", ""))
				# Fall back to first content
				return self._clean_html(contents[0].get("value", ""))

		# Try description (RSS 2.0)
		if item.get("description"):
			return self._clean_html(item.get("description", ""))

		# Try summary
		if item.get("summary"):
			return self._clean_html(item.get("summary", ""))

		return ""

	def _extract_summary(self, item, full_text):
		"""
		Extract or generate summary.

		Args:
			item: feedparser entry object
			full_text: Full text content

		Returns:
			str: Summary text
		"""
		# Try summary field
		summary = item.get("summary", "")
		if summary:
			summary = self._clean_html(summary)
			# Truncate if too long
			if len(summary) > 500:
				summary = summary[:497] + "..."
			return summary

		# Generate from full text
		if full_text:
			# Take first 500 chars
			summary = full_text[:500]
			if len(full_text) > 500:
				summary = summary[:497] + "..."
			return summary

		return ""

	def _clean_html(self, html_text):
		"""
		Clean HTML and convert to plain text.

		Args:
			html_text: HTML string

		Returns:
			str: Plain text
		"""
		if not html_text:
			return ""

		try:
			from bs4 import BeautifulSoup

			soup = BeautifulSoup(html_text, "html.parser")
			# Remove script and style elements
			for element in soup(["script", "style"]):
				element.decompose()
			return soup.get_text(separator=" ", strip=True)
		except ImportError:
			# Fallback: simple regex
			import re

			text = re.sub(r"<[^>]+>", " ", html_text)
			text = re.sub(r"\s+", " ", text)
			return text.strip()

	def _classify_document_type(self, item):
		"""
		Classify document type from RSS entry.

		Args:
			item: feedparser entry object

		Returns:
			str: Document type
		"""
		# Check categories
		categories = item.get("tags", []) or item.get("categories", [])
		for cat in categories:
			cat_term = cat.get("term", "").lower() if isinstance(cat, dict) else str(cat).lower()

			if "rule" in cat_term:
				return "Rule"
			elif "guidance" in cat_term:
				return "Guidance"
			elif "release" in cat_term:
				return "Release"
			elif "enforcement" in cat_term:
				return "Enforcement"

		# Check title
		title = item.get("title", "").lower()

		if "final rule" in title:
			return "Rule"
		elif "proposed rule" in title:
			return "Proposed Rule"
		elif "interpretive" in title or "interpretation" in title:
			return "Interpretation"
		elif "guidance" in title:
			return "Guidance"
		elif "amendment" in title:
			return "Amendment"
		elif "enforcement" in title:
			return "Enforcement"
		elif "staff bulletin" in title:
			return "Staff Bulletin"

		return "Release"
