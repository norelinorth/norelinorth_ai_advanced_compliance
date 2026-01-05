# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Connector Factory

Provides the get_connector function to instantiate the appropriate
connector based on feed type.
"""

import frappe
from frappe import _


def get_connector(feed_source):
	"""
	Get the appropriate connector for a feed source.

	Args:
		feed_source: Regulatory Feed Source document or name

	Returns:
		BaseConnector: Connector instance for the feed type

	Raises:
		frappe.ValidationError: If feed type is not supported
	"""
	if isinstance(feed_source, str):
		feed_source = frappe.get_doc("Regulatory Feed Source", feed_source)

	feed_type = feed_source.feed_type

	if feed_type == "RSS":
		from .rss_connector import RSSConnector

		return RSSConnector(feed_source)

	elif feed_type == "SEC EDGAR":
		from .sec_edgar import SECEdgarConnector

		return SECEdgarConnector(feed_source)

	elif feed_type == "PCAOB":
		from .pcaob import PCAOBConnector

		return PCAOBConnector(feed_source)

	elif feed_type == "Custom API":
		from .custom_api import CustomAPIConnector

		return CustomAPIConnector(feed_source)

	else:
		frappe.throw(_("Unsupported feed type: {0}").format(feed_type))
