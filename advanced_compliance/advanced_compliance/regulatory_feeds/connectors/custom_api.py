# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Custom API Connector

Handles fetching from custom REST APIs for regulatory content.
"""

import frappe
from frappe import _
from frappe.utils import getdate

from .base_connector import BaseConnector


class CustomAPIConnector(BaseConnector):
	"""
	Connector for custom REST APIs.

	Supports JSON APIs that return regulatory updates
	in a configurable format.
	"""

	def fetch_updates(self):
		"""
		Fetch updates from custom API.

		Expected API response format:
		{
			"items": [
				{
					"title": "...",
					"date": "YYYY-MM-DD",
					"summary": "...",
					"content": "...",
					"url": "...",
					"type": "..."
				}
			]
		}

		Returns:
			list: List of parsed update dicts
		"""
		try:
			import requests
		except ImportError:
			frappe.throw(
				_(
					"requests package is required for Custom API. "
					"Please install it with: pip install requests"
				)
			)

		try:
			headers = {"User-Agent": self.user_agent, "Accept": "application/json"}

			# Add API key if configured
			if self.feed_source.api_key:
				api_key = self.feed_source.get_password("api_key")
				headers["Authorization"] = f"Bearer {api_key}"

			response = requests.get(self.url, headers=headers, timeout=30)
			response.raise_for_status()
			data = response.json()

		except Exception as e:
			self._log_error(_("Failed to fetch from API"), e)
			return []

		# Parse response
		items = data.get("items", [])
		if not items and isinstance(data, list):
			items = data

		updates = []
		for item in items:
			parsed = self.parse_item(item)
			if parsed:
				title = parsed.get("title", "")
				if self._filter_by_keywords(title):
					doc_type = parsed.get("document_type", "")
					if self._filter_by_document_types(doc_type):
						updates.append(parsed)

		return updates

	def parse_item(self, item):
		"""
		Parse API response item.

		Args:
			item: Dict from API response

		Returns:
			dict: Parsed update data or None
		"""
		# Extract date with fallbacks
		pub_date = None
		for date_field in ["date", "published", "created", "publication_date"]:
			if item.get(date_field):
				try:
					pub_date = getdate(item.get(date_field))
					break
				except Exception:
					pass

		# Skip if older than last sync
		if self.last_sync and pub_date:
			if pub_date < getdate(self.last_sync):
				return None

		# Extract title with fallbacks
		title = item.get("title") or item.get("name") or item.get("subject", "")

		# Extract summary with fallbacks
		summary = (item.get("summary") or item.get("description") or item.get("excerpt", ""))[:2000]

		# Extract full text with fallbacks
		full_text = item.get("content") or item.get("body") or item.get("full_text") or summary

		# Extract URL with fallbacks
		url = item.get("url") or item.get("link") or item.get("href", "")

		# Extract document type with fallbacks
		doc_type = item.get("type") or item.get("document_type") or item.get("category") or "Other"

		return {
			"title": title[:255],
			"publication_date": pub_date,
			"summary": summary,
			"full_text": full_text,
			"original_url": url,
			"regulatory_body": self.feed_source.regulatory_body,
			"document_type": doc_type,
		}
