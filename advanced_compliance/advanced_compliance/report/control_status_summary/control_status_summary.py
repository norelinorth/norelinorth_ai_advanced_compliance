"""
Control Status Summary Report

Provides an overview of control activities with test status and effectiveness.
"""

import frappe
from frappe import _


def execute(filters=None):
	"""Execute the Control Status Summary report."""
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	summary = get_summary(data)

	return columns, data, None, chart, summary


def get_columns():
	"""Return report columns."""
	return [
		{
			"fieldname": "name",
			"label": _("Control ID"),
			"fieldtype": "Link",
			"options": "Control Activity",
			"width": 120,
		},
		{"fieldname": "control_name", "label": _("Control Name"), "fieldtype": "Data", "width": 250},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "control_type", "label": _("Type"), "fieldtype": "Data", "width": 100},
		{"fieldname": "is_key_control", "label": _("Key Control"), "fieldtype": "Check", "width": 80},
		{
			"fieldname": "control_owner",
			"label": _("Owner"),
			"fieldtype": "Link",
			"options": "User",
			"width": 150,
		},
		{"fieldname": "last_test_result", "label": _("Last Test Result"), "fieldtype": "Data", "width": 150},
		{"fieldname": "last_test_date", "label": _("Last Test Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "next_test_date", "label": _("Next Test Due"), "fieldtype": "Date", "width": 110},
		{"fieldname": "test_status", "label": _("Test Status"), "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	"""Get report data."""
	conditions = get_conditions(filters)

	controls = frappe.db.sql(
		f"""
        SELECT
            name,
            control_name,
            status,
            control_type,
            is_key_control,
            control_owner,
            last_test_result,
            last_test_date,
            next_test_date
        FROM `tabControl Activity`
        WHERE 1=1 {conditions}
        ORDER BY status, control_name
        """,
		filters,
		as_dict=True,
	)

	today = frappe.utils.getdate(frappe.utils.nowdate())

	for control in controls:
		# Determine test status
		if not control.next_test_date:
			control["test_status"] = "Not Scheduled"
		elif frappe.utils.getdate(control.next_test_date) < today:
			control["test_status"] = "Overdue"
		elif frappe.utils.date_diff(control.next_test_date, today) <= 7:
			control["test_status"] = "Due Soon"
		else:
			control["test_status"] = "On Track"

	return controls


def get_conditions(filters):
	"""Build SQL conditions from filters."""
	conditions = []

	if filters and filters.get("status"):
		conditions.append("AND status = %(status)s")

	if filters and filters.get("control_type"):
		conditions.append("AND control_type = %(control_type)s")

	if filters and filters.get("is_key_control"):
		conditions.append("AND is_key_control = 1")

	if filters and filters.get("control_owner"):
		conditions.append("AND control_owner = %(control_owner)s")

	return " ".join(conditions)


def get_chart_data(data):
	"""Generate chart data for the report."""
	status_counts = {}
	for row in data:
		status = row.get("status") or "Unknown"
		status_counts[status] = status_counts.get(status, 0) + 1

	return {
		"data": {
			"labels": list(status_counts.keys()),
			"datasets": [{"name": _("Controls"), "values": list(status_counts.values())}],
		},
		"type": "donut",
		"colors": ["#ffc107", "#28a745", "#17a2b8", "#dc3545"],
	}


def get_summary(data):
	"""Generate summary statistics."""
	total = len(data)
	active = sum(1 for d in data if d.get("status") == "Active")
	key_controls = sum(1 for d in data if d.get("is_key_control"))
	effective = sum(1 for d in data if d.get("last_test_result") == "Effective")
	overdue = sum(1 for d in data if d.get("test_status") == "Overdue")

	effectiveness_rate = (effective / active * 100) if active > 0 else 0

	return [
		{"value": total, "label": _("Total Controls"), "datatype": "Int"},
		{"value": active, "label": _("Active Controls"), "datatype": "Int", "indicator": "green"},
		{"value": key_controls, "label": _("Key Controls"), "datatype": "Int", "indicator": "blue"},
		{
			"value": f"{effectiveness_rate:.1f}%",
			"label": _("Effectiveness Rate"),
			"datatype": "Data",
			"indicator": "green" if effectiveness_rate >= 80 else "orange",
		},
		{
			"value": overdue,
			"label": _("Tests Overdue"),
			"datatype": "Int",
			"indicator": "red" if overdue > 0 else "green",
		},
	]
