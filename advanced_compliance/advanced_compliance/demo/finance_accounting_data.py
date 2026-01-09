# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Finance and Accounting Compliance Demo Data Generator.

Creates realistic compliance data for testing:
- Control Categories (Financial reporting, Treasury, etc.)
- Risk Categories (Financial, Operational, Compliance risks)
- COSO Principles (17 principles across 5 components)
- Control Activities (SOX-style internal controls)
- Risk Register Entries (Financial/Accounting risks)
- Evidence Capture Rules (For financial documents)
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, getdate, nowdate


def setup_finance_accounting_data():
	"""
	Main function to set up all Finance & Accounting compliance data.

	Returns:
	    dict: Summary of created records
	"""
	frappe.flags.in_demo_data = True

	summary = {
		"control_categories": 0,
		"risk_categories": 0,
		"coso_principles": 0,
		"controls": 0,
		"risks": 0,
		"capture_rules": 0,
	}

	try:
		# Create in dependency order
		summary["control_categories"] = create_control_categories()
		summary["risk_categories"] = create_risk_categories()
		summary["coso_principles"] = create_coso_principles()
		summary["controls"] = create_control_activities()
		summary["risks"] = create_risk_register_entries()
		summary["capture_rules"] = create_evidence_capture_rules()

		frappe.db.commit()

	finally:
		frappe.flags.in_demo_data = False

	return summary


def create_control_categories():
	"""Create Finance & Accounting control categories."""
	categories = [
		{
			"category_name": "Financial Reporting",
			"description": "Controls over financial statement preparation and reporting accuracy",
		},
		{
			"category_name": "Revenue Recognition",
			"description": "Controls ensuring revenue is recorded in accordance with accounting standards",
			"parent_category": "Financial Reporting",
		},
		{
			"category_name": "Expense Management",
			"description": "Controls over expense recording, approval, and classification",
			"parent_category": "Financial Reporting",
		},
		{
			"category_name": "Treasury & Cash Management",
			"description": "Controls over cash, banking, and treasury operations",
		},
		{
			"category_name": "Bank Reconciliation",
			"description": "Controls ensuring bank accounts are properly reconciled",
			"parent_category": "Treasury & Cash Management",
		},
		{
			"category_name": "Payment Processing",
			"description": "Controls over payment authorization and execution",
			"parent_category": "Treasury & Cash Management",
		},
		{
			"category_name": "Accounts Receivable",
			"description": "Controls over customer billing, collections, and AR aging",
		},
		{
			"category_name": "Credit Management",
			"description": "Controls over customer credit limits and terms",
			"parent_category": "Accounts Receivable",
		},
		{
			"category_name": "Accounts Payable",
			"description": "Controls over vendor payments and AP processing",
		},
		{
			"category_name": "Invoice Processing",
			"description": "Controls over vendor invoice receipt and approval",
			"parent_category": "Accounts Payable",
		},
		{
			"category_name": "Fixed Assets",
			"description": "Controls over asset capitalization, depreciation, and disposal",
		},
		{
			"category_name": "Inventory & Cost of Sales",
			"description": "Controls over inventory valuation and COGS calculation",
		},
		{
			"category_name": "Payroll",
			"description": "Controls over employee compensation and payroll processing",
		},
		{
			"category_name": "Tax Compliance",
			"description": "Controls over tax calculation, reporting, and filing",
		},
		{
			"category_name": "Intercompany Transactions",
			"description": "Controls over intercompany billing, transfers, and eliminations",
		},
		{
			"category_name": "Period-End Close",
			"description": "Controls over month-end and year-end closing procedures",
		},
		{
			"category_name": "Journal Entries",
			"description": "Controls over manual journal entry preparation and approval",
			"parent_category": "Period-End Close",
		},
		{
			"category_name": "IT General Controls",
			"description": "Controls over financial systems access and change management",
		},
		{
			"category_name": "Segregation of Duties",
			"description": "Controls ensuring proper separation of incompatible functions",
		},
	]

	created = 0
	for cat in categories:
		if not frappe.db.exists("Control Category", {"category_name": cat["category_name"]}):
			doc = frappe.get_doc({"doctype": "Control Category", **cat})
			doc.insert(ignore_permissions=True)
			created += 1

	return created


def create_risk_categories():
	"""Create Finance & Accounting risk categories."""
	categories = [
		{
			"category_name": "Financial Reporting Risk",
			"description": "Risks related to material misstatement in financial statements",
		},
		{
			"category_name": "Revenue Misstatement",
			"description": "Risk of incorrect revenue recognition or timing",
			"parent_category": "Financial Reporting Risk",
		},
		{
			"category_name": "Expense Misclassification",
			"description": "Risk of expenses recorded in wrong period or category",
			"parent_category": "Financial Reporting Risk",
		},
		{"category_name": "Fraud Risk", "description": "Risks related to fraudulent activities"},
		{
			"category_name": "Asset Misappropriation",
			"description": "Risk of theft or misuse of company assets",
			"parent_category": "Fraud Risk",
		},
		{
			"category_name": "Financial Statement Fraud",
			"description": "Risk of intentional misstatement of financial results",
			"parent_category": "Fraud Risk",
		},
		{"category_name": "Liquidity Risk", "description": "Risk of insufficient cash to meet obligations"},
		{"category_name": "Credit Risk", "description": "Risk of customer non-payment or default"},
		{
			"category_name": "Regulatory Compliance Risk",
			"description": "Risk of non-compliance with financial regulations",
		},
		{
			"category_name": "Tax Risk",
			"description": "Risk of tax penalties or unexpected liabilities",
			"parent_category": "Regulatory Compliance Risk",
		},
		{
			"category_name": "Operational Risk",
			"description": "Risk of loss from inadequate processes or systems",
		},
		{
			"category_name": "System Failure Risk",
			"description": "Risk of financial system downtime or data loss",
			"parent_category": "Operational Risk",
		},
		{"category_name": "Vendor Risk", "description": "Risk related to third-party vendor performance"},
		{"category_name": "Currency Risk", "description": "Risk from foreign exchange rate fluctuations"},
		{
			"category_name": "Interest Rate Risk",
			"description": "Risk from changes in interest rates affecting borrowing costs",
		},
	]

	created = 0
	for cat in categories:
		if not frappe.db.exists("Risk Category", {"category_name": cat["category_name"]}):
			doc = frappe.get_doc({"doctype": "Risk Category", **cat})
			doc.insert(ignore_permissions=True)
			created += 1

	return created


def create_coso_principles():
	"""Create COSO Internal Control Framework principles."""
	principles = [
		# Control Environment (Principles 1-5)
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
			"title": "Accountability for Internal Control",
			"description": "The organization holds individuals accountable for their internal control responsibilities.",
		},
		# Risk Assessment (Principles 6-9)
		{
			"principle_number": 6,
			"component": "Risk Assessment",
			"title": "Specify Suitable Objectives",
			"description": "The organization specifies objectives with sufficient clarity to enable identification of risks.",
		},
		{
			"principle_number": 7,
			"component": "Risk Assessment",
			"title": "Identify and Analyze Risks",
			"description": "The organization identifies risks to the achievement of its objectives and analyzes risks.",
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
			"title": "Identify and Assess Changes",
			"description": "The organization identifies and assesses changes that could significantly impact internal control.",
		},
		# Control Activities (Principles 10-12)
		{
			"principle_number": 10,
			"component": "Control Activities",
			"title": "Select and Develop Control Activities",
			"description": "The organization selects and develops control activities that mitigate risks.",
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
		# Information & Communication (Principles 13-15)
		{
			"principle_number": 13,
			"component": "Information and Communication",
			"title": "Use Relevant Quality Information",
			"description": "The organization obtains or generates and uses relevant, quality information.",
		},
		{
			"principle_number": 14,
			"component": "Information and Communication",
			"title": "Communicate Internally",
			"description": "The organization internally communicates information necessary to support internal control.",
		},
		{
			"principle_number": 15,
			"component": "Information and Communication",
			"title": "Communicate Externally",
			"description": "The organization communicates with external parties regarding internal control matters.",
		},
		# Monitoring Activities (Principles 16-17)
		{
			"principle_number": 16,
			"component": "Monitoring Activities",
			"title": "Conduct Ongoing and Separate Evaluations",
			"description": "The organization conducts ongoing and/or separate evaluations of internal control.",
		},
		{
			"principle_number": 17,
			"component": "Monitoring Activities",
			"title": "Evaluate and Communicate Deficiencies",
			"description": "The organization evaluates and communicates internal control deficiencies timely.",
		},
	]

	created = 0
	for p in principles:
		# Check by principle_number since that has a unique constraint
		if not frappe.db.exists("COSO Principle", {"principle_number": p["principle_number"]}):
			doc = frappe.get_doc({"doctype": "COSO Principle", **p})
			doc.insert(ignore_permissions=True)
			created += 1

	return created


def create_control_activities():
	"""Create Finance & Accounting control activities."""

	# Get categories for linking
	def get_category(name):
		return frappe.db.get_value("Control Category", {"category_name": name}, "name")

	controls = [
		# Revenue Recognition Controls
		{
			"control_name": "Revenue Recognition Review",
			"description": "Monthly review of revenue transactions to ensure compliance with ASC 606 revenue recognition criteria. Includes verification of performance obligations, transaction price, and timing.",
			"control_category": get_category("Revenue Recognition"),
			"control_type": "Detective",
			"automation_level": "Semi-automated",
			"frequency": "Monthly",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. Extract revenue transactions for the period
2. Review for proper revenue recognition timing
3. Verify performance obligations are met
4. Confirm transaction prices are accurate
5. Document exceptions and follow up""",
			"evidence_requirements": "Revenue register, supporting contracts, delivery confirmations",
		},
		{
			"control_name": "Sales Invoice Approval",
			"description": "All sales invoices above $10,000 require manager approval before posting. System enforces approval workflow.",
			"control_category": get_category("Revenue Recognition"),
			"control_type": "Preventive",
			"automation_level": "Fully Automated",
			"frequency": "Continuous",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. Sales invoice created by billing team
2. System routes invoices >$10K for approval
3. Manager reviews and approves/rejects
4. Approved invoices auto-post to GL""",
			"evidence_requirements": "Approval workflow logs, system configuration",
		},
		{
			"control_name": "Credit Memo Authorization",
			"description": "Credit memos require dual approval - sales manager and finance controller - before processing.",
			"control_category": get_category("Revenue Recognition"),
			"control_type": "Preventive",
			"automation_level": "Semi-automated",
			"frequency": "Event-driven",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. Credit memo request submitted with justification
2. Sales manager reviews and approves
3. Finance controller reviews and approves
4. Credit memo processed and posted""",
			"evidence_requirements": "Credit memo forms, approval signatures, supporting documentation",
		},
		# Bank Reconciliation Controls
		{
			"control_name": "Bank Reconciliation Review",
			"description": "Monthly bank reconciliations prepared by accountant and reviewed by controller within 5 business days of month-end.",
			"control_category": get_category("Bank Reconciliation"),
			"control_type": "Detective",
			"automation_level": "Semi-automated",
			"frequency": "Monthly",
			"is_key_control": 1,
			"test_frequency": "Monthly",
			"control_procedure": """1. Download bank statements on 1st business day
2. Import transactions into reconciliation tool
3. Match transactions with GL entries
4. Investigate and clear reconciling items
5. Controller reviews and signs off""",
			"evidence_requirements": "Bank statements, reconciliation reports, sign-off documentation",
		},
		{
			"control_name": "Outstanding Check Review",
			"description": "Review of checks outstanding more than 90 days with follow-up and escheatment processing as required.",
			"control_category": get_category("Bank Reconciliation"),
			"control_type": "Detective",
			"automation_level": "Manual",
			"frequency": "Quarterly",
			"is_key_control": 0,
			"test_frequency": "Annually",
			"control_procedure": """1. Generate outstanding check report
2. Identify checks >90 days old
3. Contact payees for status
4. Process escheatment if required
5. Document resolution""",
			"evidence_requirements": "Outstanding check report, correspondence, escheatment filings",
		},
		# Payment Controls
		{
			"control_name": "Payment Batch Authorization",
			"description": "All payment batches require dual authorization before release. Treasury manager and CFO approval required for batches over $100,000.",
			"control_category": get_category("Payment Processing"),
			"control_type": "Preventive",
			"automation_level": "Semi-automated",
			"frequency": "Daily",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. AP creates payment batch
2. Treasury manager reviews and approves
3. Batches >$100K routed to CFO
4. Approved batches released to bank""",
			"evidence_requirements": "Payment batch reports, approval logs, bank confirmations",
		},
		{
			"control_name": "Positive Pay File Transmission",
			"description": "Daily transmission of positive pay file to bank for check fraud prevention. Exceptions reviewed within 24 hours.",
			"control_category": get_category("Payment Processing"),
			"control_type": "Preventive",
			"automation_level": "Fully Automated",
			"frequency": "Daily",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. System generates positive pay file after check run
2. File transmitted to bank automatically
3. Bank matches presented checks against file
4. Exceptions emailed to treasury team
5. Treasury reviews and approves/rejects exceptions""",
			"evidence_requirements": "Transmission logs, exception reports, bank confirmations",
		},
		# Accounts Payable Controls
		{
			"control_name": "Three-Way Match",
			"description": "Automated three-way match of purchase order, goods receipt, and vendor invoice before payment approval.",
			"control_category": get_category("Invoice Processing"),
			"control_type": "Preventive",
			"automation_level": "Fully Automated",
			"frequency": "Continuous",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. Vendor invoice received and scanned
2. System matches to open PO
3. System matches to goods receipt
4. Variances flagged for review
5. Matched invoices auto-approved""",
			"evidence_requirements": "Match exception reports, system configuration, sample match documentation",
		},
		{
			"control_name": "Vendor Master Data Changes",
			"description": "All vendor master data changes (especially bank details) require manager approval and callback verification.",
			"control_category": get_category("Accounts Payable"),
			"control_type": "Preventive",
			"automation_level": "Semi-automated",
			"frequency": "Event-driven",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. Change request submitted via workflow
2. Manager approves change request
3. AP team verifies via callback to known number
4. Change implemented and logged
5. Confirmation sent to vendor""",
			"evidence_requirements": "Change request forms, callback logs, approval documentation",
		},
		{
			"control_name": "Duplicate Payment Detection",
			"description": "System check for potential duplicate invoices based on vendor, amount, and invoice number before posting.",
			"control_category": get_category("Invoice Processing"),
			"control_type": "Preventive",
			"automation_level": "Fully Automated",
			"frequency": "Continuous",
			"is_key_control": 0,
			"test_frequency": "Quarterly",
			"control_procedure": """1. Invoice entered into system
2. Duplicate check runs automatically
3. Potential duplicates flagged
4. AP reviews and confirms or releases
5. Clean invoices proceed to approval""",
			"evidence_requirements": "Duplicate detection logs, exception reports",
		},
		# Journal Entry Controls
		{
			"control_name": "Manual Journal Entry Approval",
			"description": "All manual journal entries require supporting documentation and approval based on amount thresholds.",
			"control_category": get_category("Journal Entries"),
			"control_type": "Preventive",
			"automation_level": "Semi-automated",
			"frequency": "Event-driven",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. Journal entry prepared with description and support
2. System routes for approval based on amount:
   - <$10K: Accounting manager
   - $10K-$100K: Controller
   - >$100K: CFO
3. Approver reviews support and approves
4. Entry posted to GL""",
			"evidence_requirements": "Journal entry forms, supporting documentation, approval logs",
		},
		{
			"control_name": "Recurring Journal Entry Review",
			"description": "Quarterly review of all recurring journal entries to verify continued accuracy and appropriateness.",
			"control_category": get_category("Journal Entries"),
			"control_type": "Detective",
			"automation_level": "Manual",
			"frequency": "Quarterly",
			"is_key_control": 0,
			"test_frequency": "Annually",
			"control_procedure": """1. Generate list of all recurring entries
2. Review each for continued appropriateness
3. Verify amounts are still accurate
4. Update or delete as needed
5. Document review and conclusions""",
			"evidence_requirements": "Recurring entry listing, review documentation",
		},
		{
			"control_name": "Post-Close Journal Entry Review",
			"description": "Controller reviews all journal entries posted in the close period to identify unusual or material items.",
			"control_category": get_category("Period-End Close"),
			"control_type": "Detective",
			"automation_level": "Manual",
			"frequency": "Monthly",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. Generate journal entry report for close period
2. Filter for entries above threshold
3. Review each entry for appropriateness
4. Follow up on unusual items
5. Sign off on review completion""",
			"evidence_requirements": "Journal entry report, review sign-off, follow-up documentation",
		},
		# Fixed Asset Controls
		{
			"control_name": "Capital Expenditure Authorization",
			"description": "Capital expenditures require approval based on dollar thresholds and board approval for amounts over $500,000.",
			"control_category": get_category("Fixed Assets"),
			"control_type": "Preventive",
			"automation_level": "Semi-automated",
			"frequency": "Event-driven",
			"is_key_control": 1,
			"test_frequency": "Annually",
			"control_procedure": """1. Capital request submitted with justification
2. Routed for approval based on amount:
   - <$50K: Department head
   - $50K-$500K: CFO
   - >$500K: Board of Directors
3. Approved requests become authorized budget
4. Assets capitalized upon completion""",
			"evidence_requirements": "Capital request forms, approval documentation, board minutes",
		},
		{
			"control_name": "Physical Asset Verification",
			"description": "Annual physical verification of all fixed assets with reconciliation to the fixed asset register.",
			"control_category": get_category("Fixed Assets"),
			"control_type": "Detective",
			"automation_level": "Manual",
			"frequency": "Annually",
			"is_key_control": 1,
			"test_frequency": "Annually",
			"control_procedure": """1. Generate fixed asset register
2. Perform physical count by location
3. Compare count to register
4. Investigate and resolve variances
5. Update register as needed
6. Document results and sign off""",
			"evidence_requirements": "Count sheets, reconciliation documentation, variance analysis",
		},
		# Segregation of Duties Controls
		{
			"control_name": "SOD Conflict Monitoring",
			"description": "Quarterly review of user access to identify and remediate segregation of duties conflicts.",
			"control_category": get_category("Segregation of Duties"),
			"control_type": "Detective",
			"automation_level": "Semi-automated",
			"frequency": "Quarterly",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. Run SOD conflict report from system
2. Review identified conflicts
3. Validate compensating controls exist
4. Remediate conflicts where possible
5. Document exceptions with justification""",
			"evidence_requirements": "SOD conflict report, remediation documentation, exception approvals",
		},
		# IT Controls
		{
			"control_name": "Financial System Access Review",
			"description": "Quarterly review of user access to financial systems with certification by business owners.",
			"control_category": get_category("IT General Controls"),
			"control_type": "Detective",
			"automation_level": "Semi-automated",
			"frequency": "Quarterly",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. Generate user access reports for all financial systems
2. Distribute to business owners for review
3. Owners certify appropriate access
4. IT removes inappropriate access
5. Document completion""",
			"evidence_requirements": "Access reports, certification forms, removal confirmations",
		},
		{
			"control_name": "Privileged Access Monitoring",
			"description": "Monthly review of privileged user activities in financial systems to detect unauthorized changes.",
			"control_category": get_category("IT General Controls"),
			"control_type": "Detective",
			"automation_level": "Semi-automated",
			"frequency": "Monthly",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. Extract privileged user activity logs
2. Review for unauthorized or unusual activities
3. Investigate anomalies
4. Report findings to IT security
5. Document review completion""",
			"evidence_requirements": "Activity logs, review documentation, investigation reports",
		},
		# Intercompany Controls
		{
			"control_name": "Intercompany Balance Reconciliation",
			"description": "Monthly reconciliation of intercompany balances between all entities with investigation of differences.",
			"control_category": get_category("Intercompany Transactions"),
			"control_type": "Detective",
			"automation_level": "Semi-automated",
			"frequency": "Monthly",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. Extract intercompany balances from all entities
2. Compare corresponding account pairs
3. Identify and investigate differences
4. Clear timing differences
5. Escalate unreconciled items
6. Sign off on reconciliation""",
			"evidence_requirements": "Intercompany reconciliation reports, difference analysis",
		},
		{
			"control_name": "Intercompany Elimination Review",
			"description": "Review of intercompany elimination entries during consolidation to ensure completeness and accuracy.",
			"control_category": get_category("Intercompany Transactions"),
			"control_type": "Detective",
			"automation_level": "Manual",
			"frequency": "Monthly",
			"is_key_control": 1,
			"test_frequency": "Quarterly",
			"control_procedure": """1. Review elimination entries generated
2. Verify all IC balances are eliminated
3. Check elimination amounts tie to reconciliations
4. Confirm no residual IC balances in consolidated
5. Document review and sign off""",
			"evidence_requirements": "Elimination entries, consolidation package, sign-off",
		},
	]

	created = 0
	for ctrl in controls:
		if not frappe.db.exists("Control Activity", {"control_name": ctrl["control_name"]}):
			# Set last test date to random date in past 3 months for some controls
			if ctrl.get("is_key_control"):
				ctrl["last_test_date"] = add_days(nowdate(), -45)
				ctrl["last_test_result"] = "Effective"

			doc = frappe.get_doc(
				{"doctype": "Control Activity", "control_owner": "Administrator", "status": "Active", **ctrl}
			)
			doc.insert(ignore_permissions=True)
			created += 1

	return created


def create_risk_register_entries():
	"""Create Finance & Accounting risk register entries."""

	def get_category(name):
		return frappe.db.get_value("Risk Category", {"category_name": name}, "name")

	# Helper functions to convert int to expected Select field format
	likelihood_map = {
		1: "1 - Rare",
		2: "2 - Unlikely",
		3: "3 - Possible",
		4: "4 - Likely",
		5: "5 - Almost Certain",
	}

	impact_map = {1: "1 - Low", 2: "2 - Medium", 3: "3 - High", 4: "4 - Critical"}

	def get_likelihood(val):
		return likelihood_map.get(val, "3 - Possible")

	def get_impact(val):
		return impact_map.get(val, "2 - Medium")

	risks = [
		{
			"risk_name": "Revenue Recognition Timing Errors",
			"description": "Risk that revenue is recognized in the wrong period, leading to material misstatement of financial results. Could result from improper cutoff procedures or misapplication of revenue recognition standards.",
			"risk_category": get_category("Revenue Misstatement"),
			"status": "Open",
			"inherent_likelihood": 3,
			"inherent_impact": 4,
			"residual_likelihood": 2,
			"residual_impact": 3,
			"risk_owner": "Administrator",
			"mitigation_strategy": """- Monthly revenue cutoff review
- ASC 606 compliance training
- Automated system controls for revenue posting
- Quarterly internal audit testing""",
		},
		{
			"risk_name": "Fraudulent Expense Reimbursements",
			"description": "Risk of employees submitting false or inflated expense reports for personal gain. Could include fictitious expenses, duplicate submissions, or personal expenses claimed as business.",
			"risk_category": get_category("Asset Misappropriation"),
			"status": "Open",
			"inherent_likelihood": 4,
			"inherent_impact": 2,
			"residual_likelihood": 2,
			"residual_impact": 2,
			"risk_owner": "Administrator",
			"mitigation_strategy": """- Receipt requirements for all expenses
- Manager approval required
- Random audits of expense reports
- Analytics to detect patterns""",
		},
		{
			"risk_name": "Vendor Payment Fraud",
			"description": "Risk of fraudulent payments to fictitious vendors or altered payment details for legitimate vendors. Business email compromise (BEC) attacks are increasing this risk.",
			"risk_category": get_category("Asset Misappropriation"),
			"status": "Open",
			"inherent_likelihood": 4,
			"inherent_impact": 4,
			"residual_likelihood": 2,
			"residual_impact": 3,
			"risk_owner": "Administrator",
			"mitigation_strategy": """- Vendor master data change controls
- Callback verification for bank details
- Positive pay implementation
- Dual approval for payments
- Anti-fraud training""",
		},
		{
			"risk_name": "Cash Flow Shortfall",
			"description": "Risk of insufficient cash to meet operational and debt obligations. Could result from poor forecasting, customer collection issues, or unexpected expenses.",
			"risk_category": get_category("Liquidity Risk"),
			"status": "Open",
			"inherent_likelihood": 2,
			"inherent_impact": 5,
			"residual_likelihood": 1,
			"residual_impact": 4,
			"risk_owner": "Administrator",
			"mitigation_strategy": """- 13-week cash flow forecasting
- Credit facility maintenance
- AR aging monitoring
- Investment policy for excess cash""",
		},
		{
			"risk_name": "Customer Credit Losses",
			"description": "Risk of material bad debt from customer defaults or bankruptcies. Economic downturns or industry concentration could amplify losses.",
			"risk_category": get_category("Credit Risk"),
			"status": "Open",
			"inherent_likelihood": 3,
			"inherent_impact": 3,
			"residual_likelihood": 2,
			"residual_impact": 3,
			"risk_owner": "Administrator",
			"mitigation_strategy": """- Credit limit policies
- Customer credit reviews
- Credit insurance for large accounts
- AR aging monitoring and collection procedures""",
		},
		{
			"risk_name": "Tax Filing Errors",
			"description": "Risk of errors in tax returns leading to penalties, interest, or reputational damage. Complexity of multi-jurisdictional tax compliance increases this risk.",
			"risk_category": get_category("Tax Risk"),
			"status": "Open",
			"inherent_likelihood": 3,
			"inherent_impact": 3,
			"residual_likelihood": 2,
			"residual_impact": 2,
			"risk_owner": "Administrator",
			"mitigation_strategy": """- Tax calendar and tracking
- External tax advisor review
- Tax provision reconciliation
- Transfer pricing documentation""",
		},
		{
			"risk_name": "Financial System Outage",
			"description": "Risk of ERP or financial system downtime impacting period-end close, payment processing, or financial reporting. Extended outage could cause compliance violations.",
			"risk_category": get_category("System Failure Risk"),
			"status": "Open",
			"inherent_likelihood": 2,
			"inherent_impact": 4,
			"residual_likelihood": 1,
			"residual_impact": 3,
			"risk_owner": "Administrator",
			"mitigation_strategy": """- Disaster recovery plan
- Regular backup testing
- Redundant systems
- Business continuity procedures""",
		},
		{
			"risk_name": "Inventory Valuation Errors",
			"description": "Risk of material misstatement in inventory valuation due to obsolescence, incorrect costing, or physical count discrepancies.",
			"risk_category": get_category("Financial Reporting Risk"),
			"status": "Open",
			"inherent_likelihood": 3,
			"inherent_impact": 3,
			"residual_likelihood": 2,
			"residual_impact": 2,
			"risk_owner": "Administrator",
			"mitigation_strategy": """- Cycle counting program
- Obsolescence reserve analysis
- Standard cost reviews
- Physical inventory at year-end""",
		},
		{
			"risk_name": "Unauthorized Access to Financial Data",
			"description": "Risk of unauthorized users accessing, modifying, or extracting sensitive financial data. Could lead to fraud, compliance violations, or competitive harm.",
			"risk_category": get_category("Operational Risk"),
			"status": "Open",
			"inherent_likelihood": 3,
			"inherent_impact": 4,
			"residual_likelihood": 2,
			"residual_impact": 3,
			"risk_owner": "Administrator",
			"mitigation_strategy": """- Role-based access controls
- Quarterly access reviews
- Privileged access monitoring
- Multi-factor authentication""",
		},
		{
			"risk_name": "Foreign Exchange Losses",
			"description": "Risk of material losses from adverse foreign currency movements on international transactions, intercompany balances, or foreign subsidiary translations.",
			"risk_category": get_category("Currency Risk"),
			"status": "Open",
			"inherent_likelihood": 4,
			"inherent_impact": 3,
			"residual_likelihood": 3,
			"residual_impact": 2,
			"risk_owner": "Administrator",
			"mitigation_strategy": """- FX exposure monitoring
- Hedging program
- Natural hedging through operations
- Intercompany netting""",
		},
		{
			"risk_name": "Payroll Processing Errors",
			"description": "Risk of incorrect employee payments due to system errors, unauthorized changes, or data entry mistakes. Could result in compliance violations and employee dissatisfaction.",
			"risk_category": get_category("Operational Risk"),
			"status": "Open",
			"inherent_likelihood": 3,
			"inherent_impact": 2,
			"residual_likelihood": 2,
			"residual_impact": 2,
			"risk_owner": "Administrator",
			"mitigation_strategy": """- Pre-payroll review
- Segregation of duties
- Change audit trails
- Employee verification portal""",
		},
		{
			"risk_name": "Financial Statement Manipulation",
			"description": "Risk of intentional manipulation of financial results by management to meet targets, maintain stock price, or obtain financing. Material weakness in controls.",
			"risk_category": get_category("Financial Statement Fraud"),
			"status": "Open",
			"inherent_likelihood": 2,
			"inherent_impact": 5,
			"residual_likelihood": 1,
			"residual_impact": 4,
			"risk_owner": "Administrator",
			"mitigation_strategy": """- Board audit committee oversight
- Whistleblower hotline
- External audit scrutiny
- Tone at the top emphasis
- Analytical review procedures""",
		},
	]

	created = 0
	for risk in risks:
		if not frappe.db.exists("Risk Register Entry", {"risk_name": risk["risk_name"]}):
			# Convert integer likelihood/impact to Select field format
			risk_data = {
				"doctype": "Risk Register Entry",
				"risk_name": risk["risk_name"],
				"description": risk["description"],
				"risk_category": risk.get("risk_category"),
				"status": risk.get("status", "Open"),
				"risk_owner": risk.get("risk_owner"),
				"inherent_likelihood": get_likelihood(risk.get("inherent_likelihood", 3)),
				"inherent_impact": get_impact(risk.get("inherent_impact", 2)),
				"residual_likelihood": get_likelihood(risk.get("residual_likelihood", 2)),
				"residual_impact": get_impact(risk.get("residual_impact", 2)),
			}
			doc = frappe.get_doc(risk_data)
			doc.insert(ignore_permissions=True)
			created += 1

	return created


def create_evidence_capture_rules():
	"""Create evidence capture rules for financial documents."""
	# Get a control activity to link to
	control = frappe.db.get_value("Control Activity", {"control_name": "Three-Way Match"}, "name")

	if not control:
		control = frappe.db.get_value("Control Activity", {}, "name")

	rules = [
		{
			"rule_name": "Capture Sales Invoice on Submit",
			"enabled": 1,
			"control_activity": control,
			"source_doctype": "Sales Invoice",
			"trigger_event": "on_submit",
			"capture_document_pdf": 1,
			"capture_workflow_history": 1,
			"capture_version_history": 1,
			"capture_comments": 1,
		},
		{
			"rule_name": "Capture Purchase Invoice on Submit",
			"enabled": 1,
			"control_activity": control,
			"source_doctype": "Purchase Invoice",
			"trigger_event": "on_submit",
			"capture_document_pdf": 1,
			"capture_workflow_history": 1,
			"capture_version_history": 1,
			"capture_comments": 1,
		},
		{
			"rule_name": "Capture Journal Entry on Submit",
			"enabled": 1,
			"control_activity": control,
			"source_doctype": "Journal Entry",
			"trigger_event": "on_submit",
			"capture_document_pdf": 1,
			"capture_workflow_history": 1,
			"capture_version_history": 1,
			"capture_comments": 1,
		},
		{
			"rule_name": "Capture Payment Entry on Submit",
			"enabled": 1,
			"control_activity": control,
			"source_doctype": "Payment Entry",
			"trigger_event": "on_submit",
			"capture_document_pdf": 1,
			"capture_workflow_history": 1,
			"capture_version_history": 1,
			"capture_comments": 1,
		},
	]

	created = 0
	for rule in rules:
		if not frappe.db.exists("Evidence Capture Rule", {"rule_name": rule["rule_name"]}):
			doc = frappe.get_doc({"doctype": "Evidence Capture Rule", **rule})
			doc.insert(ignore_permissions=True)
			created += 1

	return created


@frappe.whitelist()
def generate_finance_accounting_data():
	"""
	API endpoint to generate Finance & Accounting compliance data.

	Returns:
	    dict: Summary of created records
	"""
	if not frappe.has_permission("Control Activity", "create"):
		frappe.throw(_("Insufficient permissions to generate demo data"))

	return setup_finance_accounting_data()


@frappe.whitelist()
def clear_finance_accounting_data():
	"""
	API endpoint to clear generated Finance & Accounting compliance data.

	Returns:
	    dict: Summary of deleted records
	"""
	if not frappe.has_permission("Control Activity", "delete"):
		frappe.throw(_("Insufficient permissions to delete demo data"))

	summary = {
		"capture_rules": 0,
		"risks": 0,
		"controls": 0,
		"coso_principles": 0,
		"risk_categories": 0,
		"control_categories": 0,
	}

	# Delete in reverse dependency order
	# Evidence Capture Rules
	for name in frappe.get_all("Evidence Capture Rule", pluck="name"):
		frappe.delete_doc("Evidence Capture Rule", name, force=True)
		summary["capture_rules"] += 1

	# Risk Register Entries
	for name in frappe.get_all("Risk Register Entry", pluck="name"):
		frappe.delete_doc("Risk Register Entry", name, force=True)
		summary["risks"] += 1

	# Control Activities
	for name in frappe.get_all("Control Activity", pluck="name"):
		frappe.delete_doc("Control Activity", name, force=True)
		summary["controls"] += 1

	# COSO Principles
	for name in frappe.get_all("COSO Principle", pluck="name"):
		frappe.delete_doc("COSO Principle", name, force=True)
		summary["coso_principles"] += 1

	# Risk Categories (delete children first for nested sets)
	# Get all risk categories, ordered by lft DESC to delete children before parents
	risk_cats = frappe.db.sql(
		"""
		SELECT name FROM `tabRisk Category`
		ORDER BY lft DESC
	""",
		as_dict=True,
	)
	for cat in risk_cats:
		try:
			frappe.delete_doc("Risk Category", cat.name, force=True, ignore_on_trash=True)
			summary["risk_categories"] += 1
		except Exception:
			# Skip if already deleted or has issues
			pass

	# Control Categories (delete children first for nested sets)
	# Get all control categories, ordered by lft DESC to delete children before parents
	control_cats = frappe.db.sql(
		"""
		SELECT name FROM `tabControl Category`
		ORDER BY lft DESC
	""",
		as_dict=True,
	)
	for cat in control_cats:
		try:
			frappe.delete_doc("Control Category", cat.name, force=True, ignore_on_trash=True)
			summary["control_categories"] += 1
		except Exception:
			# Skip if already deleted or has issues
			pass

	frappe.db.commit()
	return summary
