# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Demo Data Generator for Advanced Compliance

Generates realistic demo data for marketplace preview and evaluation.
"""

import random

import frappe
from frappe import _
from frappe.utils import add_days, add_months, nowdate, random_string

# Control templates using valid DocType field options
CONTROL_TEMPLATES = [
	{"name": "Revenue Recognition Review", "type": "Detective", "freq": "Monthly", "key": True},
	{
		"name": "Segregation of Duties - Accounts Payable",
		"type": "Preventive",
		"freq": "Continuous",
		"key": True,
	},
	{"name": "Journal Entry Approval", "type": "Preventive", "freq": "Daily", "key": True},
	{"name": "Bank Reconciliation", "type": "Detective", "freq": "Monthly", "key": True},
	{"name": "Access Review - Financial Systems", "type": "Detective", "freq": "Quarterly", "key": True},
	{"name": "Vendor Master Data Changes", "type": "Detective", "freq": "Weekly", "key": True},
	{"name": "Customer Credit Limit Approval", "type": "Preventive", "freq": "Event-driven", "key": False},
	{"name": "Inventory Count Verification", "type": "Detective", "freq": "Monthly", "key": True},
	{"name": "Fixed Asset Reconciliation", "type": "Detective", "freq": "Quarterly", "key": False},
	{"name": "Payroll Processing Review", "type": "Detective", "freq": "Weekly", "key": True},
	{"name": "Purchase Order Approval", "type": "Preventive", "freq": "Event-driven", "key": False},
	{"name": "Invoice Three-Way Match", "type": "Preventive", "freq": "Daily", "key": True},
	{"name": "System Backup Verification", "type": "Detective", "freq": "Daily", "key": False},
	{"name": "User Access Provisioning", "type": "Preventive", "freq": "Event-driven", "key": False},
	{"name": "Financial Close Checklist", "type": "Detective", "freq": "Monthly", "key": True},
	{"name": "Intercompany Reconciliation", "type": "Detective", "freq": "Monthly", "key": True},
	{"name": "Tax Calculation Review", "type": "Detective", "freq": "Quarterly", "key": False},
	{"name": "Budget vs Actual Analysis", "type": "Detective", "freq": "Monthly", "key": False},
	{"name": "Contract Review and Approval", "type": "Preventive", "freq": "Event-driven", "key": False},
	{"name": "Physical Security Access", "type": "Preventive", "freq": "Continuous", "key": False},
]

# Risk templates - impact: 1-4 (Low to Critical), likelihood: 1-5 (Rare to Almost Certain)
RISK_TEMPLATES = [
	{
		"name": "Material Misstatement in Financial Statements",
		"impact": "4 - Critical",
		"like": "3 - Possible",
	},
	{"name": "Fraud - Misappropriation of Assets", "impact": "4 - Critical", "like": "2 - Unlikely"},
	{"name": "Unauthorized System Access", "impact": "3 - High", "like": "3 - Possible"},
	{"name": "Regulatory Non-Compliance", "impact": "4 - Critical", "like": "2 - Unlikely"},
	{"name": "Data Breach - Customer Information", "impact": "4 - Critical", "like": "2 - Unlikely"},
	{"name": "Revenue Recognition Errors", "impact": "3 - High", "like": "3 - Possible"},
	{"name": "Inventory Shrinkage", "impact": "2 - Medium", "like": "4 - Likely"},
	{"name": "Vendor Fraud", "impact": "3 - High", "like": "2 - Unlikely"},
	{"name": "Payroll Processing Errors", "impact": "2 - Medium", "like": "3 - Possible"},
	{"name": "System Downtime - Critical Systems", "impact": "3 - High", "like": "3 - Possible"},
	{"name": "Contract Non-Compliance", "impact": "3 - High", "like": "2 - Unlikely"},
	{"name": "Tax Reporting Errors", "impact": "3 - High", "like": "2 - Unlikely"},
	{"name": "Business Continuity Failure", "impact": "4 - Critical", "like": "1 - Rare"},
	{"name": "Segregation of Duties Violation", "impact": "3 - High", "like": "3 - Possible"},
	{"name": "Fixed Asset Misstatement", "impact": "2 - Medium", "like": "2 - Unlikely"},
]


@frappe.whitelist()
def generate_demo_data():
	"""
	Generate realistic demo data for marketplace preview.

	Returns:
		dict: Summary of generated data
	"""
	if not frappe.has_permission("Control Activity", "create"):
		frappe.throw(_("Insufficient permissions to generate demo data"))

	results = {"controls": 0, "risks": 0, "tests": 0, "deficiencies": 0, "updates": 0}

	# Generate controls
	control_names = []
	for template in CONTROL_TEMPLATES:
		try:
			doc = frappe.get_doc(
				{
					"doctype": "Control Activity",
					"control_name": f"[DEMO] {template['name']}",
					"control_type": template["type"],
					"frequency": template["freq"],
					"is_key_control": template["key"],
					"status": "Active",
					"control_owner": "Administrator",
					"description": f"Demo control for {template['name'].lower()}. This control ensures proper {template['type'].lower()} measures are in place.",
				}
			)
			doc.insert(ignore_permissions=True)
			control_names.append(doc.name)
			results["controls"] += 1
		except Exception as e:
			# Skip if control already exists or validation fails
			frappe.log_error(
				message=f"Failed to create demo control: {str(e)}", title="Demo Data Generation Warning"
			)

	# Generate risks
	risk_names = []
	for template in RISK_TEMPLATES:
		try:
			doc = frappe.get_doc(
				{
					"doctype": "Risk Register Entry",
					"risk_name": f"[DEMO] {template['name']}",
					"inherent_impact": template["impact"],
					"inherent_likelihood": template["like"],
					"status": "Open",
					"risk_owner": "Administrator",
				}
			)
			doc.insert(ignore_permissions=True)
			risk_names.append(doc.name)
			results["risks"] += 1
		except Exception as e:
			# Skip if risk already exists or validation fails
			frappe.log_error(
				message=f"Failed to create demo risk: {str(e)}", title="Demo Data Generation Warning"
			)

	# Generate test executions (Test Execution uses 'control' field, not 'control_activity')
	test_results = ["Effective", "Effective", "Effective", "Ineffective - Minor", "Ineffective - Significant"]
	for control_name in control_names[:10]:  # Test first 10 controls
		for i in range(3):  # 3 tests per control
			try:
				test_date = add_days(nowdate(), -30 * (i + 1))
				result = random.choice(test_results)

				doc = frappe.get_doc(
					{
						"doctype": "Test Execution",
						"control": control_name,
						"test_date": test_date,
						"tester": "Administrator",
						"sample_size": random.randint(10, 50),
						"test_result": result,
					}
				)
				doc.insert(ignore_permissions=True)
				results["tests"] += 1

				# Create deficiency for ineffective tests
				if "Ineffective" in result:
					severity_map = {
						"Ineffective - Minor": "Control Deficiency",
						"Ineffective - Significant": "Significant Deficiency",
						"Ineffective - Material": "Material Weakness",
					}
					def_doc = frappe.get_doc(
						{
							"doctype": "Deficiency",
							"control": control_name,
							"description": f"[DEMO] Control test failed: {control_name}. The test result was {result}.",
							"severity": severity_map.get(result, "Control Deficiency"),
							"status": random.choice(["Open", "In Progress", "Closed"]),
							"remediation_owner": "Administrator",
							"target_date": add_days(nowdate(), random.randint(30, 90)),
						}
					)
					def_doc.insert(ignore_permissions=True)
					results["deficiencies"] += 1

			except Exception as e:
				# Skip if test execution or deficiency creation fails
				frappe.log_error(
					message=f"Failed to create demo test execution: {str(e)}",
					title="Demo Data Generation Warning",
				)

	# Generate regulatory updates
	update_titles = [
		"SEC Final Rule: Climate-Related Disclosures",
		"PCAOB AS 3101 Amendment - Audit Report",
		"FASB ASU 2024-01: Digital Assets",
		"SEC Staff Bulletin: Materiality Assessment",
		"PCAOB Guidance on Audit Evidence",
	]

	for title in update_titles:
		try:
			doc = frappe.get_doc(
				{
					"doctype": "Regulatory Update",
					"title": f"[DEMO] {title}",
					"regulatory_body": random.choice(["SEC", "PCAOB", "FASB"]),
					"document_type": random.choice(["Rule", "Guidance", "Amendment"]),
					"publication_date": add_days(nowdate(), -random.randint(1, 60)),
					"effective_date": add_days(nowdate(), random.randint(30, 180)),
					"status": random.choice(["New", "Pending Review", "Reviewed"]),
					"summary": f"Demo regulatory update regarding {title.lower()}.",
				}
			)
			doc.insert(ignore_permissions=True)
			results["updates"] += 1
		except Exception as e:
			# Skip if regulatory update already exists
			frappe.log_error(
				message=f"Failed to create demo regulatory update: {str(e)}",
				title="Demo Data Generation Warning",
			)

	frappe.db.commit()

	return {"status": "success", "message": _("Demo data generated successfully"), "results": results}


@frappe.whitelist()
def clear_demo_data():
	"""
	Remove all demo data (records starting with [DEMO]).

	Returns:
		dict: Summary of deleted records
	"""
	if not frappe.has_permission("Control Activity", "delete"):
		frappe.throw(_("Insufficient permissions to clear demo data"))

	results = {"controls": 0, "risks": 0, "tests": 0, "deficiencies": 0, "updates": 0}

	# Delete in order of dependencies
	doctypes = [
		("Deficiency", "deficiencies"),
		("Test Execution", "tests"),
		("Control Activity", "controls"),
		("Risk Register Entry", "risks"),
		("Regulatory Update", "updates"),
	]

	# Field mapping for demo data filtering
	demo_filter_fields = {
		"Control Activity": "control_name",
		"Risk Register Entry": "risk_name",
		"Deficiency": "description",
		"Test Execution": "control_name",  # Uses fetch_from control
		"Regulatory Update": "title",
	}

	for doctype, key in doctypes:
		if frappe.db.table_exists(f"tab{doctype}"):
			filter_field = demo_filter_fields.get(doctype, "name")
			records = frappe.get_all(doctype, filters=[[filter_field, "like", "%[DEMO]%"]], pluck="name")

			for name in records:
				try:
					frappe.delete_doc(doctype, name, force=True)
					results[key] += 1
				except Exception as e:
					# Skip if document cannot be deleted (linked records, etc.)
					frappe.log_error(
						message=f"Failed to delete demo {doctype} {name}: {str(e)}",
						title="Demo Data Cleanup Warning",
					)

	frappe.db.commit()

	return {"status": "success", "message": _("Demo data cleared successfully"), "results": results}
