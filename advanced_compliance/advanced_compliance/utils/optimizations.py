# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Query optimizations for Advanced Compliance

Provides optimized database queries for common operations.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt


def get_controls_with_stats(filters=None, limit=100, offset=0):
	"""
	Optimized query to get controls with aggregated statistics.

	Uses single query with JOINs instead of N+1 queries.

	Args:
		filters: Optional filters dict
		limit: Maximum records to return
		offset: Pagination offset

	Returns:
		list: Controls with statistics
	"""
	conditions = "WHERE ca.status != 'Deprecated'"

	if filters:
		if filters.get("status"):
			conditions += " AND ca.status = %(status)s"
		if filters.get("control_owner"):
			conditions += " AND ca.control_owner = %(control_owner)s"
		if filters.get("is_key_control"):
			conditions += " AND ca.is_key_control = 1"

	query = f"""
		SELECT
			ca.name,
			ca.control_name,
			ca.status,
			ca.control_owner,
			ca.control_type,
			ca.frequency,
			ca.is_key_control,
			COUNT(DISTINCT te.name) as test_count,
			COUNT(DISTINCT ce.name) as evidence_count,
			COUNT(DISTINCT d.name) as deficiency_count,
			MAX(te.test_date) as last_test_date,
			SUM(CASE WHEN d.status NOT IN ('Closed', 'Cancelled') THEN 1 ELSE 0 END) as open_deficiencies
		FROM `tabControl Activity` ca
		LEFT JOIN `tabTest Execution` te ON te.control = ca.name
		LEFT JOIN `tabControl Evidence` ce ON ce.control_activity = ca.name
		LEFT JOIN `tabDeficiency` d ON d.control = ca.name
		{conditions}
		GROUP BY ca.name
		ORDER BY ca.is_key_control DESC, ca.control_name
		LIMIT %(limit)s OFFSET %(offset)s
	"""

	params = {"limit": cint(limit), "offset": cint(offset), **(filters or {})}

	return frappe.db.sql(query, params, as_dict=True)


def get_risk_heatmap_data():
	"""
	Optimized query for risk heatmap visualization.

	Single query instead of multiple iterations.

	Returns:
		list: Risk counts by impact/likelihood
	"""
	return frappe.db.sql(
		"""
		SELECT
			inherent_impact,
			inherent_likelihood,
			COUNT(*) as count,
			GROUP_CONCAT(name SEPARATOR ', ') as risk_names
		FROM `tabRisk Register Entry`
		WHERE status = 'Open'
		GROUP BY inherent_impact, inherent_likelihood
	""",
		as_dict=True,
	)


def get_compliance_summary():
	"""
	Dashboard summary with optimized aggregations.

	Returns:
		dict: Compliance statistics
	"""
	# Check if tables exist first
	tables_exist = {
		"Control Activity": frappe.db.table_exists("tabControl Activity"),
		"Risk Register Entry": frappe.db.table_exists("tabRisk Register Entry"),
		"Deficiency": frappe.db.table_exists("tabDeficiency"),
		"Test Execution": frappe.db.table_exists("tabTest Execution"),
		"Regulatory Update": frappe.db.table_exists("tabRegulatory Update"),
		"Control Evidence": frappe.db.table_exists("tabControl Evidence"),
	}

	result = {
		"active_controls": 0,
		"key_controls": 0,
		"active_risks": 0,
		"open_deficiencies": 0,
		"pending_tests": 0,
		"new_updates": 0,
		"total_evidence": 0,
	}

	if tables_exist["Control Activity"]:
		result["active_controls"] = frappe.db.count("Control Activity", filters={"status": "Active"})
		result["key_controls"] = frappe.db.count("Control Activity", filters={"is_key_control": 1})

	if tables_exist["Risk Register Entry"]:
		result["active_risks"] = frappe.db.count("Risk Register Entry", filters={"status": "Open"})

	if tables_exist["Deficiency"]:
		result["open_deficiencies"] = frappe.db.count(
			"Deficiency", filters={"status": ["not in", ["Closed", "Cancelled"]]}
		)

	if tables_exist["Test Execution"]:
		# Test Execution is submittable - docstatus 0 = Draft/Pending
		result["pending_tests"] = frappe.db.count("Test Execution", filters={"docstatus": 0})

	if tables_exist["Regulatory Update"]:
		result["new_updates"] = frappe.db.count("Regulatory Update", filters={"status": "New"})

	if tables_exist["Control Evidence"]:
		result["total_evidence"] = frappe.db.count("Control Evidence")

	return result


def get_control_effectiveness_scores(limit=20):
	"""
	Get controls ranked by effectiveness score.

	Args:
		limit: Number of controls to return

	Returns:
		list: Controls with effectiveness metrics
	"""
	return frappe.db.sql(
		"""
		SELECT
			ca.name,
			ca.control_name,
			ca.is_key_control,
			COUNT(DISTINCT te.name) as total_tests,
			SUM(CASE WHEN te.test_result = 'Effective' THEN 1 ELSE 0 END) as passed_tests,
			ROUND(
				SUM(CASE WHEN te.test_result = 'Effective' THEN 1 ELSE 0 END) * 100.0 /
				NULLIF(COUNT(DISTINCT te.name), 0),
				1
			) as effectiveness_score
		FROM `tabControl Activity` ca
		LEFT JOIN `tabTest Execution` te ON te.control = ca.name
			AND te.docstatus = 1
		WHERE ca.status = 'Active'
		GROUP BY ca.name
		HAVING total_tests > 0
		ORDER BY effectiveness_score ASC, ca.is_key_control DESC
		LIMIT %(limit)s
	""",
		{"limit": cint(limit)},
		as_dict=True,
	)


def get_overdue_tests(days_overdue=30):
	"""
	Get controls with overdue testing.

	Args:
		days_overdue: Number of days past due

	Returns:
		list: Controls needing testing
	"""
	return frappe.db.sql(
		"""
		SELECT
			ca.name,
			ca.control_name,
			ca.control_owner,
			ca.test_frequency,
			MAX(te.test_date) as last_test_date,
			DATEDIFF(CURDATE(), MAX(te.test_date)) as days_since_test
		FROM `tabControl Activity` ca
		LEFT JOIN `tabTest Execution` te ON te.control = ca.name
			AND te.docstatus = 1
		WHERE ca.status = 'Active'
			AND ca.test_frequency IS NOT NULL
		GROUP BY ca.name
		HAVING days_since_test > %(days_overdue)s OR last_test_date IS NULL
		ORDER BY days_since_test DESC
	""",
		{"days_overdue": cint(days_overdue)},
		as_dict=True,
	)


def get_deficiency_aging():
	"""
	Get deficiency aging analysis.

	Returns:
		dict: Deficiency counts by age bucket
	"""
	return frappe.db.sql(
		"""
		SELECT
			CASE
				WHEN DATEDIFF(CURDATE(), creation) <= 30 THEN '0-30 days'
				WHEN DATEDIFF(CURDATE(), creation) <= 60 THEN '31-60 days'
				WHEN DATEDIFF(CURDATE(), creation) <= 90 THEN '61-90 days'
				ELSE '90+ days'
			END as age_bucket,
			COUNT(*) as count,
			severity
		FROM `tabDeficiency`
		WHERE status NOT IN ('Closed', 'Cancelled')
		GROUP BY age_bucket, severity
		ORDER BY
			CASE age_bucket
				WHEN '0-30 days' THEN 1
				WHEN '31-60 days' THEN 2
				WHEN '61-90 days' THEN 3
				ELSE 4
			END
	""",
		as_dict=True,
	)
