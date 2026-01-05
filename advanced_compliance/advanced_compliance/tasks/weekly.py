"""
Weekly scheduled tasks for Advanced Compliance.
"""

import frappe
from frappe import _


def generate_compliance_digest():
	"""
	Generate weekly compliance digest.

	Runs weekly via scheduler.
	"""
	settings = frappe.get_single("Compliance Settings")

	# Validate settings exist before accessing attributes
	if not settings:
		frappe.log_error(
			message=_("Compliance Settings not configured"),
			title=_("Weekly Task Skipped - generate_compliance_digest"),
		)
		return

	if not settings.enable_compliance_features:
		return

	if not settings.send_weekly_digest:
		return

	# Gather statistics
	stats = get_compliance_stats()

	# Log digest (in production, would send email)
	frappe.logger().info(f"Weekly Compliance Digest: {stats}")


def get_compliance_stats():
	"""Get compliance statistics for the digest."""
	return {
		"total_controls": frappe.db.count("Control Activity", {"status": "Active"}),
		"total_risks": frappe.db.count("Risk Register Entry", {"status": "Open"}),
		"open_deficiencies": frappe.db.count("Deficiency", {"status": ["in", ["Open", "In Progress"]]}),
		"tests_this_week": frappe.db.count(
			"Test Execution",
			{"docstatus": 1, "creation": [">=", frappe.utils.add_days(frappe.utils.nowdate(), -7)]},
		),
	}
