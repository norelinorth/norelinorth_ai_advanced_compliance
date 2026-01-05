"""
Uninstallation scripts for Advanced Compliance app.
"""

import frappe


def after_uninstall():
	"""Cleanup after uninstallation."""
	# Note: DocTypes and data are NOT automatically deleted
	# This is intentional - data preservation is important for compliance
	frappe.logger().info("Advanced Compliance uninstalled. Data preserved for compliance records.")
