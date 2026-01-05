"""
Risk Heat Map Report

Provides a visual overview of organizational risks by likelihood and impact.
"""

import frappe
from frappe import _
from frappe.utils import cint


def execute(filters=None):
	"""Execute the Risk Heat Map report."""
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
			"label": _("Risk ID"),
			"fieldtype": "Link",
			"options": "Risk Register Entry",
			"width": 120,
		},
		{"fieldname": "risk_name", "label": _("Risk Name"), "fieldtype": "Data", "width": 250},
		{
			"fieldname": "risk_category",
			"label": _("Category"),
			"fieldtype": "Link",
			"options": "Risk Category",
			"width": 130,
		},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "inherent_risk_score", "label": _("Inherent Score"), "fieldtype": "Int", "width": 100},
		{"fieldname": "residual_risk_score", "label": _("Residual Score"), "fieldtype": "Int", "width": 100},
		{"fieldname": "risk_level", "label": _("Risk Level"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "risk_owner",
			"label": _("Owner"),
			"fieldtype": "Link",
			"options": "User",
			"width": 150,
		},
		{"fieldname": "control_count", "label": _("Controls"), "fieldtype": "Int", "width": 80},
	]


def get_data(filters):
	"""Get report data."""
	conditions = get_conditions(filters)

	risks = frappe.db.sql(
		f"""
        SELECT
            r.name,
            r.risk_name,
            r.risk_category,
            r.status,
            r.inherent_risk_score,
            r.residual_risk_score,
            r.risk_owner,
            (SELECT COUNT(*) FROM `tabRisk Control Link` rcl
             WHERE rcl.parent = r.name) as control_count
        FROM `tabRisk Register Entry` r
        WHERE 1=1 {conditions}
        ORDER BY r.residual_risk_score DESC
        """,
		filters,
		as_dict=True,
	)

	# Get thresholds from settings
	settings = frappe.get_single("Compliance Settings")

	# Handle case where settings don't exist
	if not settings:
		frappe.throw(_("Please configure Compliance Settings before running this report"))

	critical_threshold = cint(settings.critical_risk_threshold)
	high_threshold = cint(settings.high_risk_threshold)
	# Medium threshold is optional - use .get() for safe access
	medium_threshold = cint(settings.get("medium_risk_threshold") or 0)

	if not critical_threshold or not high_threshold:
		frappe.throw(_("Please configure Risk Thresholds in Compliance Settings"))

	for risk in risks:
		score = risk.get("residual_risk_score") or 0
		if score >= critical_threshold:
			risk["risk_level"] = "Critical"
		elif score >= high_threshold:
			risk["risk_level"] = "High"
		elif medium_threshold and score >= medium_threshold:
			risk["risk_level"] = "Medium"
		else:
			risk["risk_level"] = "Low"

	return risks


def get_conditions(filters):
	"""Build SQL conditions from filters."""
	conditions = []

	if filters and filters.get("status"):
		conditions.append("AND r.status = %(status)s")

	if filters and filters.get("risk_category"):
		conditions.append("AND r.risk_category = %(risk_category)s")

	if filters and filters.get("risk_level"):
		# This will be filtered in Python since it's calculated
		pass

	if filters and filters.get("risk_owner"):
		conditions.append("AND r.risk_owner = %(risk_owner)s")

	return " ".join(conditions)


def get_chart_data(data):
	"""Generate chart data for the report."""
	level_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}

	for row in data:
		level = row.get("risk_level") or "Low"
		level_counts[level] = level_counts.get(level, 0) + 1

	return {
		"data": {
			"labels": list(level_counts.keys()),
			"datasets": [{"name": _("Risks"), "values": list(level_counts.values())}],
		},
		"type": "bar",
		"colors": ["#dc3545", "#fd7e14", "#ffc107", "#28a745"],
	}


def get_summary(data):
	"""Generate summary statistics."""
	total = len(data)
	critical = sum(1 for d in data if d.get("risk_level") == "Critical")
	high = sum(1 for d in data if d.get("risk_level") == "High")
	open_risks = sum(1 for d in data if d.get("status") == "Open")
	mitigated = sum(1 for d in data if d.get("status") == "Mitigated")

	return [
		{"value": total, "label": _("Total Risks"), "datatype": "Int"},
		{
			"value": critical,
			"label": _("Critical Risks"),
			"datatype": "Int",
			"indicator": "red" if critical > 0 else "green",
		},
		{
			"value": high,
			"label": _("High Risks"),
			"datatype": "Int",
			"indicator": "orange" if high > 0 else "green",
		},
		{
			"value": open_risks,
			"label": _("Open Risks"),
			"datatype": "Int",
			"indicator": "red" if open_risks > 0 else "green",
		},
		{"value": mitigated, "label": _("Mitigated"), "datatype": "Int", "indicator": "green"},
	]
