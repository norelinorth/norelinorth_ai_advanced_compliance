# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Base Connector

Abstract base class for all regulatory feed connectors.
"""

from abc import ABC, abstractmethod

import frappe
from frappe import _
from frappe.utils import now_datetime


class BaseConnector(ABC):
	"""
	Abstract base class for regulatory feed connectors.

	All connector implementations must inherit from this class
	and implement the abstract methods.
	"""

	def __init__(self, feed_source):
		"""
		Initialize connector with feed source configuration.

		Args:
			feed_source: Regulatory Feed Source document
		"""
		self.feed_source = feed_source
		self.url = feed_source.url
		self.last_sync = feed_source.last_sync
		self.user_agent = feed_source.user_agent or "AdvancedCompliance/1.0"

	@abstractmethod
	def fetch_updates(self):
		"""
		Fetch updates from the regulatory source.

		Must be implemented by subclasses.

		Returns:
			list: List of dicts with regulatory update data
		"""
		pass

	@abstractmethod
	def parse_item(self, item):
		"""
		Parse a single item from the feed.

		Must be implemented by subclasses.

		Args:
			item: Raw item from feed

		Returns:
			dict: Parsed regulatory update data with keys:
				- title (str): Update title
				- publication_date (date): Publication date
				- summary (str): Brief summary
				- full_text (str): Full content
				- original_url (str): Source URL
				- document_type (str): Type of document
				- regulatory_body (str): Issuing body
		"""
		pass

	def sync(self):
		"""
		Main sync method - fetches and saves updates.

		Fetches all updates from the source, filters for new items,
		and creates Regulatory Update documents.

		Returns:
			int: Number of new updates processed
		"""
		updates = self.fetch_updates()
		count = 0

		for update_data in updates:
			if not update_data:
				continue

			if not self._update_exists(update_data):
				try:
					self._create_update(update_data)
					count += 1
				except Exception as e:
					frappe.log_error(
						message=f"Error creating update: {str(e)}\n" f"Data: {update_data}",
						title=_("Feed Item Error: {0}").format(self.feed_source.source_name),
					)

		self._update_last_sync()
		return count

	def _update_exists(self, update_data):
		"""
		Check if update already exists based on original URL.

		Args:
			update_data: Dict with update data

		Returns:
			bool: True if update already exists
		"""
		original_url = update_data.get("original_url")
		if not original_url:
			return False

		return frappe.db.exists("Regulatory Update", {"original_url": original_url})

	def _create_update(self, update_data):
		"""
		Create Regulatory Update document.

		Args:
			update_data: Dict with update data

		Returns:
			Document: Created Regulatory Update document
		"""
		doc = frappe.get_doc(
			{
				"doctype": "Regulatory Update",
				"source": self.feed_source.name,
				"regulatory_body": update_data.get("regulatory_body") or self.feed_source.regulatory_body,
				"title": update_data.get("title", "")[:255],
				"publication_date": update_data.get("publication_date"),
				"effective_date": update_data.get("effective_date"),
				"summary": update_data.get("summary", "")[:2000],
				"full_text": update_data.get("full_text", ""),
				"original_url": update_data.get("original_url", ""),
				"document_type": update_data.get("document_type", ""),
				"status": "New",
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.commit()

		return doc

	def _update_last_sync(self):
		"""Update last sync timestamp on feed source."""
		frappe.db.set_value(
			"Regulatory Feed Source",
			self.feed_source.name,
			{"last_sync": now_datetime(), "last_sync_status": "Success"},
		)
		frappe.db.commit()

	def _log_error(self, message, error=None):
		"""
		Log error and update feed source status.

		Args:
			message: Error message
			error: Exception object (optional)
		"""
		full_message = message
		if error:
			full_message = f"{message}\n{str(error)}"

		frappe.log_error(
			message=full_message, title=_("Feed Sync Error: {0}").format(self.feed_source.source_name)
		)

		frappe.db.set_value(
			"Regulatory Feed Source",
			self.feed_source.name,
			{
				"last_sync": now_datetime(),
				"last_sync_status": "Failed",
				"last_error": str(error)[:500] if error else message[:500],
			},
		)
		frappe.db.commit()

	def _filter_by_keywords(self, text):
		"""
		Check if text matches configured keywords.

		Args:
			text: Text to check

		Returns:
			bool: True if matches keywords or no keywords configured
		"""
		keywords = self.feed_source.get("keywords", [])
		if not keywords:
			return True

		text_lower = text.lower()

		for kw in keywords:
			keyword = kw.keyword.lower()
			match_type = kw.match_type

			if match_type == "Contains":
				if keyword in text_lower:
					return True
			elif match_type == "Exact":
				if keyword == text_lower:
					return True
			elif match_type == "Regex":
				import re

				if re.search(keyword, text_lower):
					return True

		return False

	def _filter_by_document_types(self, doc_type):
		"""
		Check if document type matches configured filter.

		Args:
			doc_type: Document type string

		Returns:
			bool: True if matches filter or no filter configured
		"""
		doc_types_filter = self.feed_source.document_types
		if not doc_types_filter:
			return True

		allowed_types = [t.strip().lower() for t in doc_types_filter.split(",")]

		return doc_type.lower() in allowed_types
