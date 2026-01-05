"""
Monthly scheduled tasks for Advanced Compliance.
"""

import frappe
from frappe import _


def calculate_compliance_scores():
	"""
	Calculate and store compliance scores.

	Runs monthly via scheduler.
	"""
	settings = frappe.get_single("Compliance Settings")

	# Validate settings exist before accessing attributes
	if not settings:
		frappe.log_error(
			message=_("Compliance Settings not configured"),
			title=_("Monthly Task Skipped - calculate_compliance_scores"),
		)
		return

	if not settings.enable_compliance_features:
		return

	# Calculate control effectiveness rate
	total_controls = frappe.db.count("Control Activity", {"status": "Active"})
	effective_controls = frappe.db.count(
		"Control Activity", {"status": "Active", "last_test_result": "Effective"}
	)

	if total_controls > 0:
		effectiveness_rate = (effective_controls / total_controls) * 100
	else:
		effectiveness_rate = 0

	# Log score (in production, would store in a metrics DocType)
	frappe.logger().info(f"Monthly Compliance Score: {effectiveness_rate:.1f}% control effectiveness")
