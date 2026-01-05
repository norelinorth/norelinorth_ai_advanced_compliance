"""
Daily scheduled tasks for Advanced Compliance.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, nowdate


def check_overdue_tests():
	"""
	Check for overdue control tests and create Compliance Alerts.

	Runs daily via scheduler. Creates one alert per overdue control
	if no open alert already exists.
	"""
	settings = frappe.get_single("Compliance Settings")

	# Validate settings exist before accessing attributes
	if not settings:
		frappe.log_error(
			message=_("Compliance Settings not configured"),
			title=_("Daily Task Skipped - check_overdue_tests"),
		)
		return

	if not settings.enable_compliance_features:
		return

	today = getdate(nowdate())

	# Find controls with overdue tests
	overdue_controls = frappe.get_all(
		"Control Activity",
		filters={"status": "Active", "next_test_date": ["<", today]},
		fields=["name", "control_name", "control_owner", "next_test_date", "test_frequency"],
	)

	alerts_created = 0
	for control in overdue_controls:
		# Check if an open alert already exists for this control
		existing_alert = frappe.db.exists(
			"Compliance Alert",
			{
				"alert_type": "Overdue Test",
				"related_doctype": "Control Activity",
				"related_document": control.name,
				"status": ["in", ["New", "Acknowledged", "In Progress"]],
			},
		)

		if existing_alert:
			continue  # Skip - alert already exists

		# Calculate days overdue and determine severity
		days_overdue = (today - getdate(control.next_test_date)).days
		if days_overdue > 30:
			severity = "Critical"
		elif days_overdue > 7:
			severity = "Warning"
		else:
			severity = "Info"

		# Create Compliance Alert
		alert = frappe.get_doc(
			{
				"doctype": "Compliance Alert",
				"alert_type": "Overdue Test",
				"severity": severity,
				"status": "New",
				"title": _("Overdue Test: {0}").format(control.control_name),
				"description": _(
					"Control '{0}' has overdue testing. Due date was {1} ({2} days ago). Test frequency: {3}"
				).format(
					control.control_name,
					control.next_test_date,
					days_overdue,
					control.test_frequency or "Not set",
				),
				"related_doctype": "Control Activity",
				"related_document": control.name,
				"detection_rule": "Overdue Test Detection",
				"detection_details": frappe.as_json(
					{
						"control_id": control.name,
						"control_name": control.control_name,
						"control_owner": control.control_owner,
						"due_date": str(control.next_test_date),
						"days_overdue": days_overdue,
						"test_frequency": control.test_frequency,
					}
				),
			}
		)
		alert.insert(ignore_permissions=True)
		alerts_created += 1

		# Log for audit trail
		frappe.logger("advanced_compliance").info(
			_("Created Compliance Alert for overdue test: {0} ({1}) - {2} days overdue").format(
				control.name, control.control_name, days_overdue
			)
		)

	if alerts_created:
		frappe.db.commit()
		frappe.logger("advanced_compliance").info(
			_("Created {0} Compliance Alerts for overdue tests").format(alerts_created)
		)


def send_control_owner_reminders():
	"""
	Send reminders to control owners for upcoming tests.

	Runs daily via scheduler.
	"""
	settings = frappe.get_single("Compliance Settings")

	# Validate settings exist before accessing attributes
	if not settings:
		frappe.log_error(
			message=_("Compliance Settings not configured"),
			title=_("Daily Task Skipped - send_control_owner_reminders"),
		)
		return

	if not settings.enable_compliance_features:
		return

	if not settings.enable_email_notifications:
		return

	reminder_days = cint(settings.days_before_test_reminder)
	if not reminder_days:
		# Scheduler tasks should not throw - log and return gracefully
		frappe.log_error(
			message=_("Days Before Test Reminder not configured in Compliance Settings"),
			title=_("Compliance Reminder Configuration"),
		)
		return

	reminder_date = add_days(nowdate(), reminder_days)

	# Find controls with upcoming tests
	upcoming_tests = frappe.get_all(
		"Control Activity",
		filters={"status": "Active", "next_test_date": reminder_date},
		fields=["name", "control_name", "control_owner", "next_test_date"],
	)

	# Group by owner
	owners = {}
	for control in upcoming_tests:
		if control.control_owner not in owners:
			owners[control.control_owner] = []
		owners[control.control_owner].append(control)

	# Send reminders (placeholder - would send actual emails)
	for owner, controls in owners.items():
		# In production, would use frappe.sendmail()
		frappe.logger().info(f"Would send reminder to {owner} for {len(controls)} controls")
