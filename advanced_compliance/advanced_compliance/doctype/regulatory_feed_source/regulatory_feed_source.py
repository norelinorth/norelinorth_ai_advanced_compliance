# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class RegulatoryFeedSource(Document):
	"""
	DocType for configuring regulatory feed sources.

	Stores connection information for external regulatory data sources
	such as SEC EDGAR, PCAOB, RSS feeds, and custom APIs.
	"""

	def validate(self):
		"""Validate feed source configuration."""
		self.validate_url()
		self.validate_user_agent()

	def validate_url(self):
		"""Validate URL format."""
		if not self.url:
			frappe.throw(_("Feed URL is required"))

		if not self.url.startswith(("http://", "https://")):
			frappe.throw(_("Feed URL must start with http:// or https://"))

		# Validate URL format
		from urllib.parse import urlparse

		try:
			result = urlparse(self.url)
			if not all([result.scheme, result.netloc]):
				frappe.throw(_("Invalid URL format. Please provide a valid URL."))
		except Exception:
			frappe.throw(_("Invalid URL format. Please provide a valid URL."))

	def validate_user_agent(self):
		"""Validate user agent for SEC EDGAR."""
		if self.feed_type == "SEC EDGAR" and not self.user_agent:
			frappe.throw(
				_(
					"User Agent is required for SEC EDGAR feeds. "
					"SEC requires identification in the format: "
					"CompanyName/Version (contact@email.com)"
				)
			)

	def sync_now(self):
		"""
		Manually trigger sync for this feed source.

		Returns:
			dict: Sync results with count of new updates
		"""
		from advanced_compliance.advanced_compliance.regulatory_feeds.connectors import get_connector

		if not self.enabled:
			frappe.throw(_("Cannot sync disabled feed source"))

		try:
			connector = get_connector(self)
			count = connector.sync()

			self.db_set("last_sync", now_datetime())
			self.db_set("last_sync_status", "Success")
			self.db_set("last_error", None)

			return {
				"success": True,
				"updates_count": count,
				"message": _("{0} new updates synced").format(count),
			}
		except Exception as e:
			self.db_set("last_sync", now_datetime())
			self.db_set("last_sync_status", "Failed")
			self.db_set("last_error", str(e)[:500])

			frappe.log_error(
				message=frappe.get_traceback(), title=_("Feed Sync Error: {0}").format(self.source_name)
			)

			frappe.throw(_("Sync failed: {0}").format(str(e)))

	def get_update_count(self):
		"""
		Get count of updates from this source.

		Returns:
			int: Number of Regulatory Update documents from this source
		"""
		return frappe.db.count("Regulatory Update", filters={"source": self.name})
