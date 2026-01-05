"""
Installation scripts for Advanced Compliance app.
"""

import frappe
from frappe import _


def before_install():
	"""Pre-installation checks."""
	if "erpnext" not in frappe.get_installed_apps():
		frappe.throw(_("ERPNext must be installed before Advanced Compliance"))


def after_install():
	"""Post-installation setup."""
	# Only create roles during install - roles DocType is standard
	create_custom_roles()
	frappe.db.commit()

	# Master data will be created on first migrate after install
	# This avoids issues with DocTypes not being synced yet


def after_migrate():
	"""Run after bench migrate."""
	try:
		sync_coso_principles()
		sync_default_categories()
		create_compliance_settings()
		# Frappe v16: Add modified index for list view performance
		ensure_modified_indexes()
		frappe.db.commit()
	except Exception as e:
		# Log but don't fail migrate if master data creation fails
		frappe.log_error(
			message=f"Error creating compliance master data: {str(e)}", title=_("Advanced Compliance Setup")
		)


def ensure_modified_indexes():
	"""
	Frappe v16 Migration: Add modified index to key DocTypes.

	In Frappe v16, the default list view sorting changed from 'modified' to 'creation'.
	To maintain performance when sorting by modified (which users often expect),
	we need to explicitly add the modified index.

	See: https://github.com/frappe/frappe/wiki/Migrating-to-version-16
	"""
	# DocTypes that commonly need modified sorting
	doctypes_needing_modified_index = [
		"Control Activity",
		"Risk Register Entry",
		"Test Execution",
		"Deficiency",
		"Control Evidence",
		"Compliance Alert",
		"Risk Prediction",
		"NL Query Log",
		"Compliance Graph Entity",
		"Compliance Graph Relationship",
	]

	for doctype in doctypes_needing_modified_index:
		try:
			# Check if DocType exists
			if frappe.db.exists("DocType", doctype):
				table_name = f"tab{doctype}"
				# frappe.db.add_index is idempotent - safe to call multiple times
				frappe.db.add_index(doctype, ["modified"])
		except Exception:
			# Index might already exist or table structure issue - ignore
			pass


def create_custom_roles():
	"""Create compliance-specific roles."""
	roles = [
		{"role_name": "Compliance Admin", "desk_access": 1, "is_custom": 1},
		{"role_name": "Compliance Officer", "desk_access": 1, "is_custom": 1},
		{"role_name": "Internal Auditor", "desk_access": 1, "is_custom": 1},
		{"role_name": "Control Owner", "desk_access": 1, "is_custom": 1},
		{"role_name": "Compliance Viewer", "desk_access": 1, "is_custom": 1},
	]

	for role_data in roles:
		if not frappe.db.exists("Role", role_data["role_name"]):
			role = frappe.get_doc({"doctype": "Role", **role_data})
			role.insert(ignore_permissions=True)


def create_coso_principles():
	"""Create COSO framework principles as master data."""
	coso_principles = [
		# Control Environment
		{
			"principle_number": 1,
			"component": "Control Environment",
			"title": "Commitment to Integrity and Ethical Values",
			"description": "The organization demonstrates a commitment to integrity and ethical values.",
		},
		{
			"principle_number": 2,
			"component": "Control Environment",
			"title": "Board Independence and Oversight",
			"description": "The board of directors demonstrates independence from management and exercises oversight.",
		},
		{
			"principle_number": 3,
			"component": "Control Environment",
			"title": "Management Structure and Authority",
			"description": "Management establishes structures, reporting lines, and appropriate authorities.",
		},
		{
			"principle_number": 4,
			"component": "Control Environment",
			"title": "Commitment to Competence",
			"description": "The organization demonstrates a commitment to attract, develop, and retain competent individuals.",
		},
		{
			"principle_number": 5,
			"component": "Control Environment",
			"title": "Accountability",
			"description": "The organization holds individuals accountable for their internal control responsibilities.",
		},
		# Risk Assessment
		{
			"principle_number": 6,
			"component": "Risk Assessment",
			"title": "Specify Suitable Objectives",
			"description": "The organization specifies objectives with sufficient clarity to enable identification of risks.",
		},
		{
			"principle_number": 7,
			"component": "Risk Assessment",
			"title": "Identify and Analyze Risk",
			"description": "The organization identifies risks to the achievement of objectives and analyzes risks.",
		},
		{
			"principle_number": 8,
			"component": "Risk Assessment",
			"title": "Assess Fraud Risk",
			"description": "The organization considers the potential for fraud in assessing risks.",
		},
		{
			"principle_number": 9,
			"component": "Risk Assessment",
			"title": "Identify and Analyze Significant Change",
			"description": "The organization identifies and assesses changes that could significantly impact internal control.",
		},
		# Control Activities
		{
			"principle_number": 10,
			"component": "Control Activities",
			"title": "Select and Develop Control Activities",
			"description": "The organization selects and develops control activities that contribute to risk mitigation.",
		},
		{
			"principle_number": 11,
			"component": "Control Activities",
			"title": "Technology General Controls",
			"description": "The organization selects and develops general control activities over technology.",
		},
		{
			"principle_number": 12,
			"component": "Control Activities",
			"title": "Deploy Through Policies and Procedures",
			"description": "The organization deploys control activities through policies and procedures.",
		},
		# Information & Communication
		{
			"principle_number": 13,
			"component": "Information and Communication",
			"title": "Use Relevant Information",
			"description": "The organization obtains, generates, and uses relevant quality information.",
		},
		{
			"principle_number": 14,
			"component": "Information and Communication",
			"title": "Internal Communication",
			"description": "The organization internally communicates information necessary for internal control.",
		},
		{
			"principle_number": 15,
			"component": "Information and Communication",
			"title": "External Communication",
			"description": "The organization communicates with external parties regarding internal control matters.",
		},
		# Monitoring Activities
		{
			"principle_number": 16,
			"component": "Monitoring Activities",
			"title": "Conduct Ongoing and Separate Evaluations",
			"description": "The organization selects, develops, and performs ongoing and/or separate evaluations.",
		},
		{
			"principle_number": 17,
			"component": "Monitoring Activities",
			"title": "Evaluate and Communicate Deficiencies",
			"description": "The organization evaluates and communicates internal control deficiencies timely.",
		},
	]

	for principle in coso_principles:
		name = f"COSO-{principle['principle_number']:02d}"
		# Check by principle_number (unique field) not just name
		existing = frappe.db.exists("COSO Principle", {"principle_number": principle["principle_number"]})
		if not existing:
			doc = frappe.get_doc({"doctype": "COSO Principle", "name": name, **principle})
			doc.insert(ignore_permissions=True)


def create_default_categories():
	"""Create default control and risk categories."""
	# Control Categories
	control_categories = [
		{
			"category_name": "Financial Reporting",
			"description": "Controls over financial statement assertions",
		},
		{"category_name": "Operations", "description": "Controls over business operations"},
		{"category_name": "Compliance", "description": "Controls over regulatory compliance"},
		{"category_name": "IT General Controls", "description": "Technology and system controls"},
		{"category_name": "Entity Level Controls", "description": "Organization-wide controls"},
	]

	for cat in control_categories:
		if not frappe.db.exists("Control Category", cat["category_name"]):
			frappe.get_doc({"doctype": "Control Category", **cat}).insert(ignore_permissions=True)

	# Risk Categories
	risk_categories = [
		{"category_name": "Financial Risk", "description": "Risks to financial reporting accuracy"},
		{"category_name": "Operational Risk", "description": "Risks to business operations"},
		{"category_name": "Compliance Risk", "description": "Regulatory and legal risks"},
		{"category_name": "Strategic Risk", "description": "Risks to strategic objectives"},
		{"category_name": "Technology Risk", "description": "IT and cybersecurity risks"},
		{"category_name": "Fraud Risk", "description": "Risks of fraudulent activities"},
	]

	for cat in risk_categories:
		if not frappe.db.exists("Risk Category", cat["category_name"]):
			frappe.get_doc({"doctype": "Risk Category", **cat}).insert(ignore_permissions=True)


def create_compliance_settings():
	"""Create the Compliance Settings singleton if it doesn't exist."""
	if not frappe.db.exists("Compliance Settings", "Compliance Settings"):
		settings = frappe.get_doc(
			{
				"doctype": "Compliance Settings",
				"enable_compliance_features": 1,
				"default_test_frequency": "Quarterly",
				"risk_score_method": "Likelihood x Impact",
				"enable_email_notifications": 1,
				"days_before_test_reminder": 7,
				"high_risk_threshold": 12,
				"critical_risk_threshold": 16,
			}
		)
		settings.insert(ignore_permissions=True)


def sync_coso_principles():
	"""Sync COSO principles during migrate."""
	create_coso_principles()


def sync_default_categories():
	"""Sync default categories during migrate."""
	create_default_categories()
