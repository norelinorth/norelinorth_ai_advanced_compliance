"""
Comprehensive Test Data Setup for Advanced Compliance.

This script creates test data that populates EVERY field in every DocType
to ensure thorough testing coverage.
"""

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime, nowdate


def setup_comprehensive_test_data():
	"""
	Create comprehensive test data for all compliance DocTypes.

	This function populates ALL fields to test the complete functionality.
	"""
	frappe.set_user("Administrator")

	# Get or create test company
	company = get_or_create_test_company()

	# Get test user
	test_user = "Administrator"

	# 1. Create master data
	print("Creating master data...")
	control_categories = create_control_categories()
	risk_categories = create_risk_categories()
	coso_principles = ensure_coso_principles()
	departments = get_or_create_departments(company)

	# 2. Create Risk Register Entries (must come before controls)
	print("Creating risk register entries...")
	risks = create_risk_register_entries(risk_categories, departments, test_user, company)

	# 3. Create Control Activities with all fields populated
	print("Creating control activities...")
	controls = create_control_activities(
		control_categories, coso_principles, risks, departments, test_user, company
	)

	# 4. Link mitigating controls to risks (after controls are created)
	print("Linking mitigating controls to risks...")
	link_mitigating_controls_to_risks(risks, controls)

	# 5. Create Test Executions
	print("Creating test executions...")
	test_executions = create_test_executions(controls, test_user)

	# 6. Create Deficiencies
	print("Creating deficiencies...")
	deficiencies = create_deficiencies(controls, test_executions, test_user)

	# 7. Create Evidence Capture Rules
	print("Creating evidence capture rules...")
	capture_rules = create_evidence_capture_rules(controls)

	# 8. Create Control Evidence
	print("Creating control evidence...")
	evidence = create_control_evidence(controls, capture_rules, company, test_user)

	# 9. Create Compliance Alerts
	print("Creating compliance alerts...")
	alerts = create_compliance_alerts(controls, risks, deficiencies)

	# 10. Create Graph Entities and Relationships
	print("Creating knowledge graph data...")
	create_graph_data(controls, risks)

	# 11. Create Risk Predictions
	print("Creating risk predictions...")
	create_risk_predictions(controls)

	# 12. Create NL Query Log entries
	print("Creating NL query logs...")
	create_nl_query_logs()

	frappe.db.commit()
	print("Comprehensive test data created successfully!")

	return {
		"controls": len(controls),
		"risks": len(risks),
		"test_executions": len(test_executions),
		"deficiencies": len(deficiencies),
		"evidence": len(evidence),
		"alerts": len(alerts),
	}


def get_or_create_test_company():
	"""Get existing company or return default."""
	companies = frappe.get_all("Company", limit=1, pluck="name")
	if companies:
		return companies[0]
	return None


def get_or_create_departments(company):
	"""
	Get or create test departments for the company.

	This function tries to find existing departments first, and only creates
	new ones if necessary. Uses standard ERPNext department naming.
	"""
	departments = []

	if not company:
		print("Warning: No company found - skipping department creation")
		return departments

	# Try to find existing departments first (use standard ERPNext names)
	# Order: Accounts, Research & Development, Management, Operations, Legal
	preferred_depts = ["Accounts", "Research & Development", "Management", "Operations", "Legal"]

	for dept_name in preferred_depts:
		existing = frappe.db.get_value(
			"Department", {"department_name": dept_name, "company": company}, "name"
		)
		if existing:
			departments.append(existing)
			print(f"Using existing department: {existing}")
		else:
			# Also check without company filter (for global departments)
			existing = frappe.db.get_value("Department", dept_name, "name")
			if existing:
				departments.append(existing)
				print(f"Using existing global department: {existing}")
			else:
				# Create new department if none exists
				try:
					doc = frappe.get_doc(
						{
							"doctype": "Department",
							"department_name": dept_name,
							"company": company,
							"is_group": 0,
						}
					)
					doc.insert(ignore_permissions=True)
					departments.append(doc.name)
					print(f"Created department: {doc.name}")
				except Exception as e:
					print(f"Could not create department {dept_name}: {str(e)}")

	return departments


def create_control_categories():
	"""Create hierarchical control categories with all fields populated."""
	categories = []

	# Parent categories
	parent_cats = [
		{
			"category_name": "SOX Controls",
			"description": "Controls required for Sarbanes-Oxley compliance including ITGC and business process controls.",
			"is_group": 1,
		},
		{
			"category_name": "Operational Controls",
			"description": "Controls over day-to-day business operations and processes.",
			"is_group": 1,
		},
	]

	for cat_data in parent_cats:
		if not frappe.db.exists("Control Category", cat_data["category_name"]):
			doc = frappe.get_doc({"doctype": "Control Category", **cat_data})
			doc.insert(ignore_permissions=True)
			categories.append(doc.name)
		else:
			categories.append(cat_data["category_name"])

	# Child categories under SOX Controls
	child_cats = [
		{
			"category_name": "Revenue Recognition Controls",
			"description": "Controls over revenue recognition per ASC 606.",
			"parent_category": "SOX Controls",
			"is_group": 0,
		},
		{
			"category_name": "Accounts Payable Controls",
			"description": "Controls over the procure-to-pay process.",
			"parent_category": "SOX Controls",
			"is_group": 0,
		},
		{
			"category_name": "Journal Entry Controls",
			"description": "Controls over manual and automated journal entries.",
			"parent_category": "SOX Controls",
			"is_group": 0,
		},
	]

	for cat_data in child_cats:
		if not frappe.db.exists("Control Category", cat_data["category_name"]):
			doc = frappe.get_doc({"doctype": "Control Category", **cat_data})
			doc.insert(ignore_permissions=True)
			categories.append(doc.name)
		else:
			categories.append(cat_data["category_name"])

	return categories


def create_risk_categories():
	"""Create hierarchical risk categories with all fields populated."""
	categories = []

	parent_cats = [
		{
			"category_name": "Financial Statement Risks",
			"description": "Risks that could lead to material misstatement of financial statements.",
			"is_group": 1,
		},
		{
			"category_name": "Cyber Security Risks",
			"description": "Risks related to information security and cyber threats.",
			"is_group": 1,
		},
	]

	for cat_data in parent_cats:
		if not frappe.db.exists("Risk Category", cat_data["category_name"]):
			doc = frappe.get_doc({"doctype": "Risk Category", **cat_data})
			doc.insert(ignore_permissions=True)
			categories.append(doc.name)
		else:
			categories.append(cat_data["category_name"])

	# Child categories
	child_cats = [
		{
			"category_name": "Revenue Overstatement Risk",
			"description": "Risk that revenue is overstated through premature or fictitious recognition.",
			"parent_category": "Financial Statement Risks",
			"is_group": 0,
		},
		{
			"category_name": "Expense Understatement Risk",
			"description": "Risk that expenses are understated through improper capitalization or deferral.",
			"parent_category": "Financial Statement Risks",
			"is_group": 0,
		},
	]

	for cat_data in child_cats:
		if not frappe.db.exists("Risk Category", cat_data["category_name"]):
			doc = frappe.get_doc({"doctype": "Risk Category", **cat_data})
			doc.insert(ignore_permissions=True)
			categories.append(doc.name)
		else:
			categories.append(cat_data["category_name"])

	return categories


def ensure_coso_principles():
	"""Ensure COSO principles exist and return list of names."""
	# Use sync function that safely checks for existing principles
	from advanced_compliance.install import sync_coso_principles

	sync_coso_principles()
	return frappe.get_all("COSO Principle", order_by="principle_number asc", pluck="name")


def create_risk_register_entries(risk_categories, departments, test_user, company):
	"""Create comprehensive risk register entries with all fields populated."""
	risks = []

	# Helper to get department safely
	def get_dept(index):
		if departments and len(departments) > index:
			return departments[index]
		return departments[0] if departments else None

	risk_data = [
		{
			"risk_name": "Revenue Recognition Fraud Risk",
			"description": "<p>Risk that management or employees may manipulate revenue recognition timing or amounts to meet financial targets. This includes:</p><ul><li>Side agreements with customers</li><li>Bill and hold arrangements</li><li>Channel stuffing</li><li>Premature revenue recognition</li></ul>",
			"risk_category": risk_categories[0] if risk_categories else None,
			"status": "Open",
			"inherent_likelihood": "4 - Likely",
			"inherent_impact": "4 - Critical",
			"residual_likelihood": "2 - Unlikely",
			"residual_impact": "3 - High",
			"risk_owner": test_user,
			"department": get_dept(0),  # Finance
			"company": company,
		},
		{
			"risk_name": "Unauthorized Journal Entry Risk",
			"description": "<p>Risk that unauthorized or inappropriate journal entries are recorded, leading to material misstatement. Key concerns include:</p><ul><li>Entries without proper approval</li><li>Entries with unusual amounts or accounts</li><li>Post-close entries that bypass normal controls</li></ul>",
			"risk_category": risk_categories[0] if risk_categories else None,
			"status": "Mitigated",
			"inherent_likelihood": "3 - Possible",
			"inherent_impact": "4 - Critical",
			"residual_likelihood": "1 - Rare",
			"residual_impact": "2 - Medium",
			"risk_owner": test_user,
			"department": get_dept(1),  # Accounting
			"company": company,
		},
		{
			"risk_name": "Vendor Master Data Manipulation",
			"description": "<p>Risk of unauthorized changes to vendor master data resulting in fraudulent payments. Scenarios include:</p><ul><li>Creation of fictitious vendors</li><li>Bank account changes without verification</li><li>Duplicate vendor payments</li></ul>",
			"risk_category": risk_categories[1] if len(risk_categories) > 1 else None,
			"status": "Open",
			"inherent_likelihood": "3 - Possible",
			"inherent_impact": "3 - High",
			"residual_likelihood": "2 - Unlikely",
			"residual_impact": "2 - Medium",
			"risk_owner": test_user,
			"department": get_dept(1),  # Accounting
			"company": company,
		},
		{
			"risk_name": "Data Breach and Exfiltration",
			"description": "<p>Risk of unauthorized access to sensitive financial data. This could result in:</p><ul><li>Regulatory penalties</li><li>Reputational damage</li><li>Financial loss</li><li>Business disruption</li></ul>",
			"risk_category": risk_categories[1] if len(risk_categories) > 1 else None,
			"status": "Accepted",
			"inherent_likelihood": "4 - Likely",
			"inherent_impact": "4 - Critical",
			"residual_likelihood": "3 - Possible",
			"residual_impact": "3 - High",
			"risk_owner": test_user,
			"department": get_dept(2),  # Information Technology
			"company": company,
		},
		{
			"risk_name": "Period End Close Errors",
			"description": "<p>Risk of errors during period-end financial close process affecting accuracy of reported results.</p>",
			"risk_category": risk_categories[0] if risk_categories else None,
			"status": "Transferred",
			"inherent_likelihood": "5 - Almost Certain",
			"inherent_impact": "2 - Medium",
			"residual_likelihood": "2 - Unlikely",
			"residual_impact": "1 - Low",
			"risk_owner": test_user,
			"department": get_dept(0),  # Finance
			"company": company,
		},
	]

	for data in risk_data:
		# Check for existing by risk_name to avoid duplicates
		existing = frappe.db.get_value("Risk Register Entry", {"risk_name": data["risk_name"]}, "name")
		if not existing:
			doc = frappe.get_doc({"doctype": "Risk Register Entry", **data})
			doc.insert(ignore_permissions=True)
			risks.append(doc.name)
		else:
			risks.append(existing)

	return risks


def create_control_activities(control_categories, coso_principles, risks, departments, test_user, company):
	"""Create comprehensive control activities with ALL fields populated."""
	controls = []

	# Helper to get department safely
	def get_dept(index):
		if departments and len(departments) > index:
			return departments[index]
		return departments[0] if departments else None

	control_data = [
		{
			"control_name": "Revenue Contract Review",
			"description": "<p><strong>Control Objective:</strong> Ensure revenue is recognized only when performance obligations are satisfied.</p><p><strong>Control Activity:</strong> The Revenue Accounting Manager reviews all new contracts over $100K for proper revenue recognition treatment per ASC 606.</p>",
			"status": "Active",
			"control_category": control_categories[0] if control_categories else None,
			"control_type": "Preventive",
			"automation_level": "Manual",
			"is_key_control": 1,
			"coso_component": "Control Activities",
			"coso_principle": coso_principles[9] if len(coso_principles) > 9 else None,  # Principle 10
			"control_owner": test_user,
			"control_performer": test_user,
			"backup_performer": test_user,
			"department": get_dept(0),  # Finance
			"company": company,
			"frequency": "Event-driven",
			"timing": "Real-time",
			"test_frequency": "Quarterly",
			"control_procedure": "<p><strong>Step 1:</strong> Receive new contract notification from Sales<br><strong>Step 2:</strong> Review contract terms for performance obligations<br><strong>Step 3:</strong> Determine transaction price allocation<br><strong>Step 4:</strong> Document revenue recognition conclusion<br><strong>Step 5:</strong> Approve in revenue tracking system</p>",
			"evidence_requirements": "<p>Required evidence:<br>- Signed contract<br>- Revenue memo with ASC 606 analysis<br>- Manager approval signature<br>- System screenshot of revenue schedule</p>",
			"risks_addressed": [{"risk": risks[0]}] if risks else [],
		},
		{
			"control_name": "Journal Entry Approval Workflow",
			"description": "<p><strong>Control Objective:</strong> Prevent unauthorized journal entries from being posted.</p><p><strong>Control Activity:</strong> All manual journal entries require approval by a manager before posting. Entries over $50K require Controller approval.</p>",
			"status": "Active",
			"control_category": control_categories[2] if len(control_categories) > 2 else None,
			"control_type": "Preventive",
			"automation_level": "Semi-automated",
			"is_key_control": 1,
			"coso_component": "Control Activities",
			"coso_principle": coso_principles[11] if len(coso_principles) > 11 else None,  # Principle 12
			"control_owner": test_user,
			"control_performer": test_user,
			"backup_performer": test_user,
			"department": get_dept(1),  # Accounting
			"company": company,
			"frequency": "Continuous",
			"timing": "Real-time",
			"test_frequency": "Monthly",
			"control_procedure": "<p><strong>Workflow:</strong><br>1. Preparer creates journal entry<br>2. System routes for approval based on amount<br>3. Approver reviews support and rationale<br>4. Approver approves/rejects in system<br>5. Entry posts only after all approvals obtained</p>",
			"evidence_requirements": "<p>- Journal entry document with signatures<br>- Supporting documentation<br>- System approval trail<br>- Segregation of duties evidence</p>",
			"risks_addressed": [{"risk": risks[1]}] if len(risks) > 1 else [],
		},
		{
			"control_name": "Vendor Master Data Change Review",
			"description": "<p><strong>Control Objective:</strong> Ensure vendor master data changes are properly authorized and verified.</p><p><strong>Control Activity:</strong> All vendor bank account changes are independently verified through callback to vendor using contact info on file.</p>",
			"status": "Active",
			"control_category": control_categories[1] if len(control_categories) > 1 else None,
			"control_type": "Detective",
			"automation_level": "Manual",
			"is_key_control": 1,
			"coso_component": "Control Activities",
			"coso_principle": coso_principles[9] if len(coso_principles) > 9 else None,
			"control_owner": test_user,
			"control_performer": test_user,
			"backup_performer": None,  # Testing without backup
			"department": get_dept(1),  # Accounting
			"company": company,
			"frequency": "Daily",
			"timing": "End of Day",
			"test_frequency": "Quarterly",
			"control_procedure": "<p>1. Review daily vendor change report<br>2. For bank changes, obtain original request<br>3. Call vendor using contact on file (not from request)<br>4. Document verification conversation<br>5. Approve change only after verification</p>",
			"evidence_requirements": "<p>- Vendor change report<br>- Verification call log<br>- Updated vendor record screenshot</p>",
			"risks_addressed": [{"risk": risks[2]}] if len(risks) > 2 else [],
		},
		{
			"control_name": "System Access Review",
			"description": "<p><strong>Control Objective:</strong> Ensure user access rights are appropriate and follow least privilege principle.</p><p><strong>Control Activity:</strong> Quarterly review of all user access rights by department managers.</p>",
			"status": "Active",
			"control_category": control_categories[0] if control_categories else None,
			"control_type": "Detective",
			"automation_level": "Fully Automated",
			"is_key_control": 0,
			"coso_component": "Control Environment",
			"coso_principle": coso_principles[4] if len(coso_principles) > 4 else None,  # Principle 5
			"control_owner": test_user,
			"control_performer": test_user,
			"backup_performer": test_user,
			"department": get_dept(2),  # Information Technology
			"company": company,
			"frequency": "Quarterly",
			"timing": "End of Period",
			"test_frequency": "Annually",
			"control_procedure": "<p>1. System generates access report<br>2. Report distributed to managers<br>3. Managers certify access appropriateness<br>4. IT processes access changes<br>5. Re-certification documented</p>",
			"evidence_requirements": "<p>- Access report<br>- Manager certification<br>- Change tickets for removed access</p>",
			"risks_addressed": [{"risk": risks[3]}] if len(risks) > 3 else [],
		},
		{
			"control_name": "Month-End Close Checklist",
			"description": "<p><strong>Control Objective:</strong> Ensure all period-end close activities are completed accurately and timely.</p><p><strong>Control Activity:</strong> Controller reviews and signs off on month-end close checklist.</p>",
			"status": "Under Review",
			"control_category": control_categories[0] if control_categories else None,
			"control_type": "Corrective",
			"automation_level": "Semi-automated",
			"is_key_control": 1,
			"coso_component": "Monitoring Activities",
			"coso_principle": coso_principles[15] if len(coso_principles) > 15 else None,  # Principle 16
			"control_owner": test_user,
			"control_performer": test_user,
			"backup_performer": test_user,
			"department": get_dept(0),  # Finance
			"company": company,
			"frequency": "Monthly",
			"timing": "End of Period",
			"test_frequency": "Semi-annually",
			"control_procedure": "<p>1. Generate close checklist from template<br>2. Assign tasks to team members<br>3. Track completion status<br>4. Review for accuracy and completeness<br>5. Sign off on final checklist</p>",
			"evidence_requirements": "<p>- Signed close checklist<br>- Supporting reconciliations<br>- Variance analysis</p>",
			"risks_addressed": [{"risk": risks[4]}] if len(risks) > 4 else [],
		},
		{
			"control_name": "Deprecated Legacy Control",
			"description": "<p>This control is no longer in use and has been replaced by automated system controls.</p>",
			"status": "Deprecated",
			"control_category": control_categories[0] if control_categories else None,
			"control_type": "Detective",
			"automation_level": "Manual",
			"is_key_control": 0,
			"coso_component": "Control Activities",
			"coso_principle": None,  # Testing without COSO principle
			"control_owner": test_user,
			"control_performer": None,  # Testing without performer
			"backup_performer": None,
			"department": get_dept(3),  # Operations
			"company": company,
			"frequency": "Weekly",
			"timing": "On Demand",
			"test_frequency": None,  # Testing without test frequency
			"control_procedure": None,  # Testing without procedure
			"evidence_requirements": None,  # Testing without requirements
			"risks_addressed": [],  # Testing without risks
		},
	]

	for data in control_data:
		# Check for existing by control_name
		existing = frappe.db.get_value("Control Activity", {"control_name": data["control_name"]}, "name")
		if not existing:
			risks_addressed = data.pop("risks_addressed", [])
			doc = frappe.get_doc({"doctype": "Control Activity", **data})
			for risk_link in risks_addressed:
				doc.append("risks_addressed", risk_link)
			doc.insert(ignore_permissions=True)
			controls.append(doc.name)
		else:
			controls.append(existing)

	return controls


def link_mitigating_controls_to_risks(risks, controls):
	"""
	Link mitigating controls to risk register entries.

	This populates the mitigating_controls child table on Risk Register Entry
	with appropriate Control Activity links.
	"""
	if not risks or not controls:
		print("Warning: No risks or controls available - skipping control linking")
		return

	# Define which controls mitigate which risks
	# Each risk index maps to a list of control indices
	risk_control_mapping = [
		# Risk 0 (Revenue Recognition Fraud) -> Control 0 (Revenue Contract Review)
		[0],
		# Risk 1 (Unauthorized Journal Entry) -> Controls 1, 4 (JE Approval, Month-End Close)
		[1, 4],
		# Risk 2 (Vendor Master Data Manipulation) -> Control 2 (Vendor Master Data Change Review)
		[2],
		# Risk 3 (Data Breach) -> Controls 3, 5 (System Access Review, Legacy Control)
		[3],
		# Risk 4 (Period End Close Errors) -> Controls 4, 1 (Month-End Close, JE Approval)
		[4, 1],
	]

	for risk_idx, control_indices in enumerate(risk_control_mapping):
		if risk_idx >= len(risks):
			continue

		risk_name = risks[risk_idx]
		try:
			risk_doc = frappe.get_doc("Risk Register Entry", risk_name)

			# Check if controls are already linked
			existing_controls = {row.control for row in risk_doc.mitigating_controls}

			controls_added = 0
			for ctrl_idx in control_indices:
				if ctrl_idx >= len(controls):
					continue

				control_name = controls[ctrl_idx]
				if control_name not in existing_controls:
					risk_doc.append("mitigating_controls", {"control": control_name})
					controls_added += 1

			if controls_added > 0:
				risk_doc.save(ignore_permissions=True)
				print(f"Linked {controls_added} control(s) to risk: {risk_name}")
			else:
				print(f"Controls already linked to risk: {risk_name}")

		except Exception as e:
			print(f"Error linking controls to risk {risk_name}: {str(e)}")

	frappe.db.commit()


def create_test_executions(controls, test_user):
	"""Create test executions with all fields populated including evidence child table."""
	test_executions = []

	# Get fiscal year
	fiscal_years = frappe.get_all("Fiscal Year", limit=1, pluck="name")
	fiscal_year = fiscal_years[0] if fiscal_years else None

	if not fiscal_year:
		print("Warning: No fiscal year found - test_period will be empty")

	# Define evidence items for each test
	evidence_sets = [
		# Evidence for Effective test
		[
			{
				"evidence_type": "Screenshot",
				"description": "Revenue recognition system screenshot showing approved contracts",
			},
			{
				"evidence_type": "System Report",
				"description": "Contract listing report from Q3 with 25 sampled items highlighted",
			},
			{
				"evidence_type": "Approval Signature",
				"description": "Manager approval signatures on revenue memos",
			},
		],
		# Evidence for Ineffective - Minor test
		[
			{
				"evidence_type": "Transaction Log",
				"description": "Journal entry approval log showing 2 late approvals",
			},
			{"evidence_type": "System Report", "description": "JE posting report with approval timestamps"},
			{"evidence_type": "Email", "description": "Email confirmation of corrective action taken"},
		],
		# Evidence for Ineffective - Significant test
		[
			{
				"evidence_type": "System Report",
				"description": "Vendor master change report showing 5 exceptions",
			},
			{"evidence_type": "Screenshot", "description": "Missing callback documentation examples"},
			{
				"evidence_type": "Other",
				"description": "Interview notes with AP team regarding verification process",
			},
		],
		# Evidence for Ineffective - Material test
		[
			{
				"evidence_type": "Configuration Export",
				"description": "Access certification completion rates by department",
			},
			{"evidence_type": "System Report", "description": "List of terminated users with active access"},
			{"evidence_type": "Email", "description": "Escalation email to Audit Committee"},
			{
				"evidence_type": "Screenshot",
				"description": "HR termination report vs. IT access report comparison",
			},
		],
		# Evidence for Not Applicable test
		[
			{
				"evidence_type": "Email",
				"description": "Email from control owner confirming control under redesign",
			},
			{"evidence_type": "Other", "description": "Control redesign project plan"},
		],
	]

	test_data = [
		# Effective test
		{
			"control": controls[0],
			"test_period": fiscal_year,
			"tester": test_user,
			"test_date": add_days(nowdate(), -30),
			"sample_size": 25,
			"population_size": 150,
			"test_procedure": "<p><strong>Test Steps Performed:</strong><br>1. Selected sample of 25 contracts from Q3<br>2. Obtained contract documents and revenue memos<br>3. Verified ASC 606 analysis was documented<br>4. Confirmed manager approval obtained<br>5. Traced to revenue schedule in system</p>",
			"test_result": "Effective",
			"exceptions_found": 0,
			"conclusion": "<p>Control is operating effectively. All 25 samples had proper documentation and approval.</p>",
			"reviewer": test_user,
			"review_date": add_days(nowdate(), -25),
			"review_notes": "<p>Review complete. Agree with test conclusion. No issues noted.</p>",
			"evidence": evidence_sets[0],
		},
		# Ineffective - Minor test
		{
			"control": controls[1],
			"test_period": fiscal_year,
			"tester": test_user,
			"test_date": add_days(nowdate(), -60),
			"sample_size": 40,
			"population_size": 500,
			"test_procedure": "<p><strong>Test Objective:</strong> Verify journal entries are approved before posting.<br><br><strong>Procedure:</strong><br>1. Obtained list of all manual JEs posted in Q3<br>2. Selected random sample of 40 entries<br>3. Verified approval obtained before posting date<br>4. Documented any exceptions</p>",
			"test_result": "Ineffective - Minor",
			"exceptions_found": 2,
			"conclusion": "<p>Found 2 entries with approval obtained after posting. Both were under $5K and subsequently approved within 24 hours. Low impact deficiency.</p>",
			"reviewer": test_user,
			"review_date": add_days(nowdate(), -55),
			"review_notes": "<p>Agree with minor classification. Recommend process reminder to team.</p>",
			"evidence": evidence_sets[1],
		},
		# Ineffective - Significant test
		{
			"control": controls[2],
			"test_period": fiscal_year,
			"tester": test_user,
			"test_date": add_days(nowdate(), -90),
			"sample_size": 15,
			"population_size": 45,
			"test_procedure": "<p><strong>Test Objective:</strong> Ensure vendor bank account changes are independently verified.<br><br><strong>Procedure:</strong><br>1. Obtained all vendor bank changes in Q3<br>2. Selected all 15 high-value vendor changes<br>3. Verified callback documentation exists<br>4. Confirmed verification was completed before payment</p>",
			"test_result": "Ineffective - Significant",
			"exceptions_found": 5,
			"conclusion": "<p>5 of 15 bank account changes were not independently verified. Callback documentation missing. This represents a significant control gap.</p>",
			"reviewer": test_user,
			"review_date": add_days(nowdate(), -85),
			"review_notes": "<p>Significant deficiency confirmed. Immediate remediation required.</p>",
			"evidence": evidence_sets[2],
		},
		# Ineffective - Material test
		{
			"control": controls[3],
			"test_period": fiscal_year,
			"tester": test_user,
			"test_date": add_days(nowdate(), -120),
			"sample_size": 100,
			"population_size": 1000,
			"test_procedure": "<p><strong>Test Objective:</strong> Verify quarterly access certifications are completed timely.<br><br><strong>Procedure:</strong><br>1. Obtained Q3 access certification completion report<br>2. Compared terminated employee list to active access<br>3. Sampled 100 certifications for completeness<br>4. Verified access was removed for terminated users</p>",
			"test_result": "Ineffective - Material",
			"exceptions_found": 35,
			"conclusion": "<p>35% of access certifications were not completed by deadline. No evidence that removed users had access actually terminated. Material weakness in access management.</p>",
			"reviewer": test_user,
			"review_date": add_days(nowdate(), -115),
			"review_notes": "<p>Material weakness confirmed. Escalation to Audit Committee required.</p>",
			"evidence": evidence_sets[3],
		},
		# Not Applicable test
		{
			"control": controls[4],
			"test_period": fiscal_year,
			"tester": test_user,
			"test_date": add_days(nowdate(), -15),
			"sample_size": 0,
			"population_size": 0,
			"test_procedure": "<p><strong>Note:</strong> Control is currently under review and redesign. Testing deferred to next quarter when new control design is implemented.</p>",
			"test_result": "Not Applicable",
			"exceptions_found": 0,
			"conclusion": "<p>Testing not applicable during current period due to control being under redesign. New control design expected to be implemented by end of Q1.</p>",
			"reviewer": test_user,
			"review_date": add_days(nowdate(), -10),
			"review_notes": "<p>Confirmed with control owner that redesign is in progress. Will schedule testing once new control is operational.</p>",
			"evidence": evidence_sets[4],
		},
	]

	for i, data in enumerate(test_data):
		# Extract evidence before creating doc
		evidence_items = data.pop("evidence", [])

		# Check if test already exists for this control on this date
		existing = frappe.db.exists(
			"Test Execution", {"control": data["control"], "test_date": data["test_date"]}
		)
		if not existing:
			doc = frappe.get_doc({"doctype": "Test Execution", **data})

			# Add evidence child table rows
			for evidence in evidence_items:
				doc.append("evidence", evidence)

			doc.insert(ignore_permissions=True)
			# Submit the test execution
			doc.submit()
			test_executions.append(doc.name)
			print(f"Created Test Execution {doc.name} with {len(evidence_items)} evidence items")
		else:
			test_executions.append(existing)

	return test_executions


def create_deficiencies(controls, test_executions, test_user):
	"""Create deficiencies with all fields populated."""
	deficiencies = []

	deficiency_data = [
		{
			"control": controls[1],
			"test_execution": test_executions[1] if len(test_executions) > 1 else None,
			"severity": "Control Deficiency",
			"status": "Closed",
			"identified_date": add_days(nowdate(), -55),
			"identified_by": test_user,
			"description": "<p>Journal entries approved after posting rather than before. Two instances identified in sample of 40.</p>",
			"root_cause": "<p>Process training gap. New team member was not aware of pre-posting approval requirement.</p>",
			"remediation_plan": "<p>1. Provide refresher training to all JE preparers<br>2. Update process documentation<br>3. Implement system block for unnapproved entries</p>",
			"remediation_owner": test_user,
			"target_date": add_days(nowdate(), -30),
			"closure_date": add_days(nowdate(), -28),
			"closure_notes": "<p>Training completed 12/15. System block implemented 12/20. Retest confirmed effectiveness.</p>",
		},
		{
			"control": controls[2],
			"test_execution": test_executions[2] if len(test_executions) > 2 else None,
			"severity": "Significant Deficiency",
			"status": "In Progress",
			"identified_date": add_days(nowdate(), -85),
			"identified_by": test_user,
			"description": "<p>Vendor bank account changes processed without independent verification. 5 of 15 sampled changes lacked callback documentation.</p>",
			"root_cause": "<p>1. Verification process not consistently followed<br>2. Contact information not always available<br>3. Time pressure during month-end</p>",
			"remediation_plan": "<p>1. Implement mandatory verification workflow in system<br>2. Require contact update before bank change<br>3. Add review step for changes during close</p>",
			"remediation_owner": test_user,
			"target_date": add_days(nowdate(), 30),
			"closure_date": None,
			"closure_notes": None,
		},
		{
			"control": controls[3],
			"test_execution": test_executions[3] if len(test_executions) > 3 else None,
			"severity": "Material Weakness",
			"status": "Open",
			"identified_date": add_days(nowdate(), -115),
			"identified_by": test_user,
			"description": "<p>Material weakness in user access management. 35% of quarterly certifications incomplete. Terminated users may retain active access.</p>",
			"root_cause": "<p>1. No automated tracking of certification completion<br>2. Manager accountability gaps<br>3. IT not receiving certification results<br>4. No automated access termination</p>",
			"remediation_plan": "<p>1. Implement GRC tool for access certification<br>2. Automate access removal for terminated users<br>3. Establish escalation for incomplete certifications<br>4. Conduct immediate full access review</p>",
			"remediation_owner": test_user,
			"target_date": add_days(nowdate(), 60),
			"closure_date": None,
			"closure_notes": None,
		},
		{
			"control": controls[0],
			"test_execution": test_executions[0] if test_executions else None,
			"severity": "Control Deficiency",
			"status": "Pending Validation",
			"identified_date": add_days(nowdate(), -10),
			"identified_by": test_user,
			"description": "<p>Revenue recognition memo template outdated. Does not include ASC 606 variable consideration guidance.</p>",
			"root_cause": "<p>Template not updated after ASC 606 adoption.</p>",
			"remediation_plan": "<p>Update template to include all ASC 606 considerations.</p>",
			"remediation_owner": test_user,
			"target_date": add_days(nowdate(), 15),
			"closure_date": None,
			"closure_notes": None,
		},
		{
			"control": controls[4] if len(controls) > 4 else controls[0],
			"test_execution": test_executions[4]
			if len(test_executions) > 4
			else (test_executions[0] if test_executions else None),
			"severity": "Control Deficiency",
			"status": "Closed",
			"identified_date": add_days(nowdate(), -45),
			"identified_by": test_user,
			"description": "<p>Month-end close checklist missing sign-off for bank reconciliation step.</p>",
			"root_cause": "<p>New checklist item added without updating the approval workflow.</p>",
			"remediation_plan": "<p>1. Add bank reconciliation sign-off to checklist<br>2. Train team on updated process<br>3. Implement mandatory sign-off in system</p>",
			"remediation_owner": test_user,
			"target_date": add_days(nowdate(), -20),
			"closure_date": add_days(nowdate(), -18),
			"closure_notes": "<p>Checklist updated on 12/10. Training completed 12/12. System change deployed 12/15. Verified in January close.</p>",
		},
		{
			"control": controls[2] if len(controls) > 2 else controls[0],
			"test_execution": test_executions[2]
			if len(test_executions) > 2
			else (test_executions[0] if test_executions else None),
			"severity": "Significant Deficiency",
			"status": "Closed",
			"identified_date": add_days(nowdate(), -120),
			"identified_by": test_user,
			"description": "<p>Vendor master data changes not reviewed within 24 hours for 30% of sampled transactions.</p>",
			"root_cause": "<p>Review queue not monitored during peak periods. Insufficient staffing for review function.</p>",
			"remediation_plan": "<p>1. Implement automatic escalation for overdue reviews<br>2. Cross-train additional staff<br>3. Add real-time monitoring dashboard</p>",
			"remediation_owner": test_user,
			"target_date": add_days(nowdate(), -60),
			"closure_date": add_days(nowdate(), -55),
			"closure_notes": "<p>Escalation workflow implemented 11/20. Two additional staff trained 11/25. Dashboard deployed 11/30. Retest on 12/5 showed 100% compliance with 24-hour SLA.</p>",
		},
	]

	for data in deficiency_data:
		# Check for existing
		existing = frappe.db.exists(
			"Deficiency", {"control": data["control"], "description": data["description"][:100]}
		)
		if not existing:
			doc = frappe.get_doc({"doctype": "Deficiency", **data})
			doc.insert(ignore_permissions=True)
			deficiencies.append(doc.name)
		else:
			deficiencies.append(existing)

	return deficiencies


def create_evidence_capture_rules(controls):
	"""Create evidence capture rules with all fields populated."""
	rules = []

	if not controls:
		print("No controls found - skipping capture rule creation")
		return rules

	# Ensure we have at least one control to link to
	default_control = controls[0]

	rule_data = [
		{
			"rule_name": "Sales Invoice Evidence Capture",
			"enabled": 1,
			"source_doctype": "Sales Invoice",
			"trigger_event": "on_submit",
			"control_activity": controls[0] if len(controls) > 0 else default_control,
			"capture_document_pdf": 1,
			"capture_workflow_history": 1,
			"capture_version_history": 1,
			"capture_comments": 1,
			"linked_doctypes": "Delivery Note\nPayment Entry",
			"retention_period_years": 7,
		},
		{
			"rule_name": "Journal Entry Evidence Capture",
			"enabled": 1,
			"source_doctype": "Journal Entry",
			"trigger_event": "on_submit",
			"control_activity": controls[1] if len(controls) > 1 else default_control,
			"capture_document_pdf": 1,
			"capture_workflow_history": 1,
			"capture_version_history": 1,
			"capture_comments": 1,
			"linked_doctypes": None,
			"retention_period_years": 10,
		},
		{
			"rule_name": "Purchase Invoice Evidence Capture",
			"enabled": 1,
			"source_doctype": "Purchase Invoice",
			"trigger_event": "on_submit",
			"control_activity": controls[2] if len(controls) > 2 else default_control,
			"capture_document_pdf": 1,
			"capture_workflow_history": 1,
			"capture_version_history": 1,
			"capture_comments": 1,
			"linked_doctypes": "Purchase Order\nPayment Entry",
			"retention_period_years": 7,
		},
		{
			"rule_name": "Payment Entry Evidence Capture",
			"enabled": 1,
			"source_doctype": "Payment Entry",
			"trigger_event": "on_submit",
			"control_activity": controls[3] if len(controls) > 3 else default_control,
			"capture_document_pdf": 1,
			"capture_workflow_history": 1,
			"capture_version_history": 1,
			"capture_comments": 1,
			"linked_doctypes": "Sales Invoice\nPurchase Invoice",
			"retention_period_years": 7,
		},
	]

	for data in rule_data:
		rule_name = data["rule_name"]
		if not frappe.db.exists("Evidence Capture Rule", {"rule_name": rule_name}):
			doc = frappe.get_doc({"doctype": "Evidence Capture Rule", **data})
			doc.insert(ignore_permissions=True)
			rules.append(doc.name)
			print(f"Created capture rule: {rule_name} for {data['source_doctype']}")
		else:
			existing = frappe.db.get_value("Evidence Capture Rule", {"rule_name": rule_name}, "name")
			rules.append(existing)
			print(f"Using existing capture rule: {existing}")

	return rules


def create_control_evidence(controls, capture_rules, company, test_user):
	"""Create control evidence records with all fields populated."""
	evidence = []

	if not controls:
		print("No controls found - skipping evidence creation")
		return evidence

	if not capture_rules:
		print("No capture rules found - evidence will be created without capture_rule links")

	# Build a mapping of source_doctype to capture_rule for proper linking
	rule_by_doctype = {}
	for rule_name in capture_rules:
		rule_doctype = frappe.db.get_value("Evidence Capture Rule", rule_name, "source_doctype")
		if rule_doctype:
			rule_by_doctype[rule_doctype] = rule_name

	print(f"Capture rule mapping: {rule_by_doctype}")

	# Get real documents to reference
	sales_invoices = frappe.get_all("Sales Invoice", filters={"docstatus": 1}, limit=3, pluck="name")
	journal_entries = frappe.get_all("Journal Entry", filters={"docstatus": 1}, limit=3, pluck="name")
	purchase_invoices = frappe.get_all("Purchase Invoice", filters={"docstatus": 1}, limit=2, pluck="name")

	if not sales_invoices and not journal_entries and not purchase_invoices:
		print("No submitted documents found - skipping evidence creation")
		return evidence

	workflow_data = [
		{"action": "Created", "user": test_user, "timestamp": str(add_days(nowdate(), -5))},
		{"action": "Submitted", "user": test_user, "timestamp": str(add_days(nowdate(), -4))},
	]

	version_data = [{"version": 1, "modified_by": test_user, "changes": "Initial creation"}]

	comments_data = [
		{"user": test_user, "comment": "Approved per compliance review", "timestamp": str(nowdate())}
	]

	evidence_data = []

	# Add Sales Invoice evidence
	for i, invoice in enumerate(sales_invoices):
		control_idx = i % len(controls)  # Cycle through controls
		snapshot_data = {"doctype": "Sales Invoice", "name": invoice, "captured_at": nowdate()}
		evidence_data.append(
			{
				"control_activity": controls[control_idx],
				"capture_rule": rule_by_doctype.get("Sales Invoice"),
				"captured_at": now_datetime(),
				"evidence_hash": hashlib.sha256(json.dumps(snapshot_data).encode()).hexdigest(),
				"source_doctype": "Sales Invoice",
				"source_name": invoice,
				"source_owner": test_user,
				"source_company": company,
				"workflow_log": json.dumps(workflow_data),
				"version_history": json.dumps(version_data),
				"comments_log": json.dumps(comments_data),
				"evidence_summary": f"Evidence captured for Sales Invoice {invoice} - Control: {controls[control_idx]}",
			}
		)

	# Add Journal Entry evidence
	for i, entry in enumerate(journal_entries):
		control_idx = (i + 1) % len(controls)  # Use different controls
		snapshot_data = {"doctype": "Journal Entry", "name": entry, "captured_at": nowdate()}
		evidence_data.append(
			{
				"control_activity": controls[control_idx],
				"capture_rule": rule_by_doctype.get("Journal Entry"),
				"captured_at": now_datetime(),
				"evidence_hash": hashlib.sha256(json.dumps(snapshot_data).encode()).hexdigest(),
				"source_doctype": "Journal Entry",
				"source_name": entry,
				"source_owner": test_user,
				"source_company": company,
				"workflow_log": json.dumps(workflow_data),
				"version_history": json.dumps(version_data),
				"comments_log": json.dumps(comments_data),
				"evidence_summary": f"Evidence captured for Journal Entry {entry} - Control: {controls[control_idx]}",
			}
		)

	# Add Purchase Invoice evidence
	for i, invoice in enumerate(purchase_invoices):
		control_idx = (i + 2) % len(controls)  # Use different controls
		snapshot_data = {"doctype": "Purchase Invoice", "name": invoice, "captured_at": nowdate()}
		evidence_data.append(
			{
				"control_activity": controls[control_idx],
				"capture_rule": rule_by_doctype.get("Purchase Invoice"),
				"captured_at": now_datetime(),
				"evidence_hash": hashlib.sha256(json.dumps(snapshot_data).encode()).hexdigest(),
				"source_doctype": "Purchase Invoice",
				"source_name": invoice,
				"source_owner": test_user,
				"source_company": company,
				"workflow_log": json.dumps(workflow_data),
				"version_history": json.dumps(version_data),
				"comments_log": json.dumps(comments_data),
				"evidence_summary": f"Evidence captured for Purchase Invoice {invoice} - Control: {controls[control_idx]}",
			}
		)

	for data in evidence_data:
		# Check for existing
		existing = frappe.db.exists(
			"Control Evidence",
			{"control_activity": data["control_activity"], "source_name": data["source_name"]},
		)
		if not existing:
			doc = frappe.get_doc({"doctype": "Control Evidence", **data})
			doc.insert(ignore_permissions=True)
			evidence.append(doc.name)
			if data.get("capture_rule"):
				print(f"Created evidence {doc.name} with capture_rule: {data['capture_rule']}")
			else:
				print(
					f"Created evidence {doc.name} WITHOUT capture_rule (no matching rule for {data['source_doctype']})"
				)
		else:
			evidence.append(existing)

	return evidence


def create_compliance_alerts(controls, risks, deficiencies):
	"""Create compliance alerts with all fields populated."""
	alerts = []

	alert_data = [
		{
			"alert_type": "Anomaly",
			"severity": "Critical",
			"status": "New",
			"title": "Unusual Journal Entry Pattern Detected",
			"description": "AI detected 15 journal entries posted after business hours with similar amounts and accounts. Potential fraud indicator.",
			"related_doctype": "Control Activity",
			"related_document": controls[1] if len(controls) > 1 else None,
			"related_field": "last_test_result",
			"related_value": "Ineffective - Significant",
			"detection_rule": "after_hours_je_pattern",
			"detection_details": json.dumps(
				{
					"pattern": "after_hours_posting",
					"count": 15,
					"confidence": 0.92,
					"date_range": "2024-12-01 to 2024-12-15",
				}
			),
		},
		{
			"alert_type": "High Risk",
			"severity": "Critical",
			"status": "Acknowledged",
			"title": "Material Weakness Requires Immediate Action",
			"description": "Access management material weakness has not been remediated within target date.",
			"related_doctype": "Deficiency",
			"related_document": deficiencies[2] if len(deficiencies) > 2 else None,
			"related_field": "severity",
			"related_value": "Material Weakness",
			"detection_rule": "material_weakness_monitor",
			"detection_details": json.dumps({"days_overdue": 30, "escalation_level": 2}),
		},
		{
			"alert_type": "Overdue Test",
			"severity": "Warning",
			"status": "In Progress",
			"title": "Control Testing Overdue",
			"description": "Quarterly test for Vendor Master Data Change Review is 15 days overdue.",
			"related_doctype": "Control Activity",
			"related_document": controls[2] if len(controls) > 2 else None,
			"related_field": "next_test_date",
			"related_value": str(add_days(nowdate(), -15)),
			"detection_rule": "test_schedule_monitor",
			"detection_details": json.dumps(
				{"expected_date": str(add_days(nowdate(), -15)), "days_overdue": 15}
			),
		},
		{
			"alert_type": "Coverage Gap",
			"severity": "Warning",
			"status": "Resolved",
			"title": "Risk Without Mitigating Control",
			"description": "Data Breach risk has no active mitigating controls assigned.",
			"related_doctype": "Risk Register Entry",
			"related_document": risks[3] if len(risks) > 3 else None,
			"related_field": "mitigating_controls",
			"related_value": "0",
			"detection_rule": "control_coverage_check",
			"detection_details": json.dumps({"risk_score": 12, "required_controls": 2}),
		},
		{
			"alert_type": "Ownership Issue",
			"severity": "Info",
			"status": "Dismissed",
			"title": "Control Owner Not Active",
			"description": "Deprecated Legacy Control has owner who is no longer active in system.",
			"related_doctype": "Control Activity",
			"related_document": controls[5] if len(controls) > 5 else None,
			"related_field": "control_owner",
			"related_value": "Inactive User",
			"detection_rule": "owner_activity_check",
			"detection_details": json.dumps({"last_login": "Never", "status": "Disabled"}),
		},
		{
			"alert_type": "Pattern Alert",
			"severity": "Info",
			"status": "New",
			"title": "Increasing Deficiency Trend",
			"description": "Control Activity has 3 deficiencies in the last 90 days, up from 0 in prior period.",
			"related_doctype": "Control Activity",
			"related_document": controls[0] if controls else None,
			"related_field": "deficiency_count",
			"related_value": "3",
			"detection_rule": "trend_analysis",
			"detection_details": json.dumps(
				{"current_period": 3, "prior_period": 0, "change_percent": "N/A"}
			),
		},
		{
			"alert_type": "Anomaly",
			"severity": "Warning",
			"status": "New",
			"title": "Unusual Vendor Payment Pattern",
			"description": "Detected 5 payments to new vendors in the last week, exceeding normal baseline of 1-2.",
			"related_doctype": "Control Activity",
			"related_document": controls[2] if len(controls) > 2 else (controls[0] if controls else None),
			"related_field": "control_type",
			"related_value": "Detective",
			"detection_rule": "vendor_payment_anomaly",
			"detection_details": json.dumps(
				{"baseline_weekly": 1.5, "current_weekly": 5, "deviation_sigma": 2.3, "confidence": 0.87}
			),
		},
		{
			"alert_type": "High Risk",
			"severity": "Warning",
			"status": "Acknowledged",
			"title": "Key Control Effectiveness Below Threshold",
			"description": "Revenue Recognition Control effectiveness dropped below 90% threshold.",
			"related_doctype": "Control Activity",
			"related_document": controls[0] if controls else None,
			"related_field": "last_test_result",
			"related_value": "Ineffective - Minor",
			"detection_rule": "key_control_effectiveness",
			"detection_details": json.dumps(
				{"threshold": 0.90, "current_effectiveness": 0.85, "is_key_control": True}
			),
		},
	]

	for data in alert_data:
		# Check for existing by title
		existing = frappe.db.exists("Compliance Alert", {"title": data["title"]})
		if not existing:
			doc = frappe.get_doc({"doctype": "Compliance Alert", **data})
			doc.insert(ignore_permissions=True)
			alerts.append(doc.name)
		else:
			alerts.append(existing)

	return alerts


def create_graph_data(controls, risks):
	"""Create compliance graph entities and relationships."""
	entities = []
	relationships = []

	# Create entities for controls
	for control_id in controls[:3]:  # First 3 controls
		entity_data = {
			"entity_doctype": "Control Activity",
			"entity_id": control_id,
			"entity_type": "Control",
			"is_active": 1,
		}
		existing = frappe.db.exists(
			"Compliance Graph Entity", {"entity_doctype": "Control Activity", "entity_id": control_id}
		)
		if not existing:
			doc = frappe.get_doc({"doctype": "Compliance Graph Entity", **entity_data})
			doc.insert(ignore_permissions=True)
			entities.append(doc.name)
		else:
			entities.append(existing)

	# Create entities for risks
	for risk_id in risks[:3]:  # First 3 risks
		entity_data = {
			"entity_doctype": "Risk Register Entry",
			"entity_id": risk_id,
			"entity_type": "Risk",
			"is_active": 1,
		}
		existing = frappe.db.exists(
			"Compliance Graph Entity", {"entity_doctype": "Risk Register Entry", "entity_id": risk_id}
		)
		if not existing:
			doc = frappe.get_doc({"doctype": "Compliance Graph Entity", **entity_data})
			doc.insert(ignore_permissions=True)
			entities.append(doc.name)
		else:
			entities.append(existing)

	# Create MITIGATES relationships
	if len(entities) >= 4:  # Need at least 2 controls and 2 risks
		rel_data = [
			{
				"source_entity": entities[0],  # Control 1
				"target_entity": entities[3],  # Risk 1
				"relationship_type": "MITIGATES",
				"weight": 0.8,
				"is_active": 1,
			},
			{
				"source_entity": entities[1],  # Control 2
				"target_entity": entities[4],  # Risk 2
				"relationship_type": "MITIGATES",
				"weight": 0.9,
				"is_active": 1,
			},
			{
				"source_entity": entities[0],  # Control 1
				"target_entity": entities[1],  # Control 2
				"relationship_type": "DEPENDS_ON",
				"weight": 0.5,
				"is_active": 1,
			},
		]

		for data in rel_data:
			existing = frappe.db.exists(
				"Compliance Graph Relationship",
				{
					"source_entity": data["source_entity"],
					"target_entity": data["target_entity"],
					"relationship_type": data["relationship_type"],
				},
			)
			if not existing:
				doc = frappe.get_doc({"doctype": "Compliance Graph Relationship", **data})
				doc.insert(ignore_permissions=True)
				relationships.append(doc.name)


def create_risk_predictions(controls):
	"""Create risk prediction records with all fields populated."""
	predictions = []

	for i, control_id in enumerate(controls[:3]):
		prediction_data = {
			"control": control_id,
			"prediction_date": add_days(nowdate(), -i),  # Different dates to avoid autoname collision
			"failure_probability": 0.15 + (i * 0.1),  # 0.15, 0.25, 0.35
			"risk_level": ["Low", "Medium", "High"][i],
			"is_current": 1 if i == 0 else 0,  # Only most recent is current
			"confidence_score": 0.85 - (i * 0.05),
			"model_version": "1.0.0",
			"contributing_factors": json.dumps(
				[
					{"factor": "Days since test", "impact": "medium", "value": 30 + (i * 30)},
					{"factor": "Historical pass rate", "impact": "low", "value": 0.9 - (i * 0.1)},
				]
			),
			"recommended_actions": json.dumps(
				[
					"Schedule testing within 30 days",
					"Review control design for effectiveness",
					"Assign backup performer",
				]
			),
			"feature_values": json.dumps(
				{
					"days_since_test": 30 + (i * 30),
					"test_pass_rate": 0.9 - (i * 0.1),
					"deficiency_count": i,
					"is_key_control": 1,
					"automation_level": 0.5,
					"has_backup": 1 if i == 0 else 0,
				}
			),
			"prediction_time_ms": 150 + (i * 50),
		}

		existing = frappe.db.exists(
			"Risk Prediction", {"control": control_id, "prediction_date": prediction_data["prediction_date"]}
		)
		if not existing:
			doc = frappe.get_doc({"doctype": "Risk Prediction", **prediction_data})
			doc.insert(ignore_permissions=True)
			predictions.append(doc.name)

	return predictions


def create_nl_query_logs():
	"""Create natural language query log entries with all fields populated."""
	logs = []

	queries = [
		{
			"question": "Show me all high risk controls that are overdue for testing",
			"query_time_ms": 250,
			"feedback": "Helpful",
			"parsed_intent": json.dumps(
				{
					"intent": "list_controls",
					"filters": {"risk_level": "High", "test_overdue": True},
					"confidence": 0.95,
				}
			),
			"generated_query": "frappe.get_all('Control Activity', filters={'status': 'Active'}, fields=['name', 'control_name'])",
			"response": "Found 5 high-risk controls that are overdue for testing:\n1. Revenue Contract Review\n2. Journal Entry Approval Workflow\n3. Vendor Master Data Change Review",
			"response_data": json.dumps(
				{
					"count": 5,
					"results": [
						{"name": "CTRL-2025-00001", "control_name": "Revenue Contract Review"},
						{"name": "CTRL-2025-00002", "control_name": "Journal Entry Approval Workflow"},
					],
				}
			),
		},
		{
			"question": "What deficiencies are open for the revenue control?",
			"query_time_ms": 180,
			"feedback": "Helpful",
			"parsed_intent": json.dumps(
				{
					"intent": "list_deficiencies",
					"filters": {"control_name": "revenue", "status": "Open"},
					"confidence": 0.88,
				}
			),
			"generated_query": "frappe.get_all('Deficiency', filters={'control': ['like', '%revenue%'], 'status': 'Open'})",
			"response": "Found 2 open deficiencies for revenue-related controls.",
			"response_data": json.dumps({"count": 2, "results": []}),
		},
		{
			"question": "Which controls need backup performers assigned?",
			"query_time_ms": 320,
			"feedback": "Not Helpful",
			"parsed_intent": json.dumps(
				{
					"intent": "find_controls_without_backup",
					"filters": {"backup_performer": None},
					"confidence": 0.72,
				}
			),
			"generated_query": "frappe.get_all('Control Activity', filters={'backup_performer': ['is', 'not set']})",
			"response": "Found 3 controls without backup performers assigned.",
			"response_data": json.dumps({"count": 3, "results": []}),
		},
		{
			"question": "Summarize the compliance status",
			"query_time_ms": 450,
			"feedback": None,  # No feedback yet
			"parsed_intent": json.dumps({"intent": "compliance_summary", "filters": {}, "confidence": 0.82}),
			"generated_query": None,  # Used LLM for response
			"response": "Overall compliance status: 85% of controls are effective. 2 material weaknesses require remediation.",
			"response_data": json.dumps(
				{
					"effective_controls": 17,
					"total_controls": 20,
					"material_weaknesses": 2,
					"significant_deficiencies": 3,
				}
			),
		},
	]

	for data in queries:
		doc = frappe.get_doc({"doctype": "NL Query Log", **data})
		doc.insert(ignore_permissions=True)
		logs.append(doc.name)

	return logs


# API endpoint to trigger test data creation
@frappe.whitelist()
def create_test_data():
	"""API endpoint to create comprehensive test data."""
	if not frappe.has_permission("Control Activity", "create"):
		frappe.throw(_("Insufficient permissions to create test data"))

	result = setup_comprehensive_test_data()
	return result


# Run directly from console
if __name__ == "__main__":
	setup_comprehensive_test_data()
