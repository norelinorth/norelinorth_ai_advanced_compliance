# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
In-App Help System for Advanced Compliance

Provides contextual help for DocTypes and fields.
"""

import frappe
from frappe import _

HELP_TOPICS = {
	"Control Activity": {
		"title": _("Control Activities"),
		"description": _(
			"Controls are the policies and procedures that mitigate risks. They ensure business processes operate as intended and comply with regulations."
		),
		"fields": {
			"control_name": _(
				"A unique, descriptive name for the control (e.g., 'Journal Entry Approval Over $10,000')"
			),
			"control_type": _(
				"Preventive controls stop issues before they occur; Detective controls identify issues after they happen"
			),
			"is_key_control": _(
				"Key controls are critical for financial reporting accuracy and are subject to more rigorous testing"
			),
			"frequency": _("How often the control is performed (Daily, Weekly, Monthly, etc.)"),
			"evidence_requirements": _("What documentation proves the control operated effectively"),
			"control_owner": _("The person responsible for ensuring the control operates correctly"),
			"description": _("Detailed explanation of what the control does and how it mitigates risk"),
			"control_procedure": _("Step-by-step instructions for performing the control"),
		},
		"tips": [
			_("Start with key controls that address high-risk areas"),
			_("Link controls to specific risks they mitigate"),
			_("Define clear evidence requirements for testing"),
			_("Assign ownership to ensure accountability"),
			_("Review controls periodically for relevance"),
		],
		"workflow": [
			_("1. Create control with Draft status"),
			_("2. Document procedure and evidence requirements"),
			_("3. Link to relevant risks"),
			_("4. Activate control when ready"),
			_("5. Schedule testing based on frequency"),
			_("6. Update status based on test results"),
		],
	},
	"Risk Register Entry": {
		"title": _("Risk Register"),
		"description": _(
			"Document and assess organizational risks. The risk register helps prioritize controls and resources."
		),
		"fields": {
			"risk_title": _("Brief, clear description of the risk"),
			"risk_category": _(
				"Classification for reporting and analysis (Financial, Operational, Compliance, etc.)"
			),
			"inherent_risk_score": _("Risk level before any controls are applied (Impact x Likelihood)"),
			"residual_risk_score": _("Risk level after controls are applied"),
			"impact_rating": _("Severity if the risk materializes (1-5 scale)"),
			"likelihood_rating": _("Probability of the risk occurring (1-5 scale)"),
			"risk_owner": _("Person accountable for managing this risk"),
		},
		"tips": [
			_("Focus on risks that could materially impact the organization"),
			_("Reassess risks periodically as conditions change"),
			_("Link multiple controls to high-severity risks"),
			_("Document risk appetite and tolerance levels"),
			_("Consider both financial and reputational impacts"),
		],
	},
	"Test Execution": {
		"title": _("Control Testing"),
		"description": _(
			"Document and track control testing activities. Testing verifies that controls operate as designed."
		),
		"fields": {
			"control_activity": _("The control being tested"),
			"test_date": _("Date when testing was performed"),
			"tester": _("Person who performed the test"),
			"sample_size": _("Number of transactions/items tested"),
			"test_result": _(
				"Overall result: Effective, Ineffective - Minor/Significant/Material, or Not Applicable"
			),
			"test_procedure": _("Steps followed during testing"),
			"exceptions_noted": _("Any issues or deviations found"),
		},
		"workflow": [
			_("1. Create test execution linked to control"),
			_("2. Perform testing procedures"),
			_("3. Collect and attach evidence"),
			_("4. Document results and conclusion"),
			_("5. Submit for review"),
			_("6. Create deficiencies if issues found"),
		],
		"tips": [
			_("Test sample should be representative of the population"),
			_("Document all exceptions, even minor ones"),
			_("Attach supporting evidence for audit trail"),
			_("Complete testing promptly after execution"),
		],
	},
	"Deficiency": {
		"title": _("Deficiency Management"),
		"description": _("Track and remediate control weaknesses identified through testing or other means."),
		"fields": {
			"deficiency_title": _("Brief description of the issue"),
			"severity": _("Impact level: Critical, Major, Moderate, or Minor"),
			"control_activity": _("Control where the deficiency was found"),
			"root_cause": _("Underlying reason for the deficiency"),
			"remediation_plan": _("Steps to fix the issue"),
			"remediation_owner": _("Person responsible for fixing the issue"),
			"target_date": _("Expected completion date for remediation"),
		},
		"tips": [
			_("Address Critical and Major deficiencies first"),
			_("Identify root cause to prevent recurrence"),
			_("Set realistic remediation timelines"),
			_("Verify remediation effectiveness before closing"),
			_("Aggregate deficiencies for trend analysis"),
		],
	},
	"Regulatory Update": {
		"title": _("Regulatory Updates"),
		"description": _(
			"Track changes to regulations and standards that may impact your compliance program."
		),
		"fields": {
			"title": _("Descriptive title for the regulatory update"),
			"regulatory_body": _("Issuing authority (SEC, PCAOB, FASB, etc.)"),
			"effective_date": _("When the regulation takes effect"),
			"status": _("Current processing status of the update"),
			"summary": _("Brief overview of the regulatory change"),
		},
		"tips": [
			_("Review new updates within 24 hours of receipt"),
			_("Assess impact on existing controls"),
			_("Create action items for required changes"),
			_("Track deadlines for implementation"),
			_("Communicate changes to affected stakeholders"),
		],
	},
	"Knowledge Graph": {
		"title": _("Knowledge Graph"),
		"description": _(
			"The knowledge graph maps relationships between compliance entities, enabling impact analysis and gap detection."
		),
		"tips": [
			_("Use impact analysis to understand control dependencies"),
			_("Identify orphan risks without linked controls"),
			_("Detect single points of failure in control coverage"),
			_("Visualize the compliance network for stakeholder presentations"),
		],
	},
}


@frappe.whitelist()
def get_help(doctype, field=None):
	"""
	Get contextual help for a DocType or field.

	Args:
		doctype: DocType name
		field: Optional field name

	Returns:
		dict: Help content
	"""
	help_data = HELP_TOPICS.get(doctype, {})

	if not help_data:
		return {"title": doctype, "description": _("No help available for this DocType")}

	if field and "fields" in help_data:
		field_help = help_data["fields"].get(field)
		if field_help:
			return {
				"title": field,
				"description": field_help,
				"doctype_title": help_data.get("title", doctype),
			}
		return {"title": field, "description": _("No help available for this field")}

	return help_data


@frappe.whitelist()
def get_all_help_topics():
	"""
	Get list of all available help topics.

	Returns:
		list: Help topic summaries
	"""
	topics = []
	for doctype, data in HELP_TOPICS.items():
		topics.append(
			{
				"doctype": doctype,
				"title": data.get("title", doctype),
				"description": data.get("description", "")[:100] + "...",
			}
		)
	return topics


@frappe.whitelist()
def get_quick_start_guide():
	"""
	Get quick start guide for new users.

	Returns:
		dict: Quick start content
	"""
	return {
		"title": _("Quick Start Guide"),
		"steps": [
			{
				"number": 1,
				"title": _("Set Up Your Organization"),
				"description": _(
					"Configure company settings and compliance frameworks in Intercompany Settings."
				),
				"action": "Intercompany Settings",
			},
			{
				"number": 2,
				"title": _("Define Your Risks"),
				"description": _(
					"Document organizational risks in the Risk Register. Start with your highest-impact areas."
				),
				"action": "Risk Register Entry",
			},
			{
				"number": 3,
				"title": _("Create Control Activities"),
				"description": _(
					"Document controls that mitigate your identified risks. Link each control to relevant risks."
				),
				"action": "Control Activity",
			},
			{
				"number": 4,
				"title": _("Execute Control Tests"),
				"description": _(
					"Perform and document control testing. Attach evidence to support your conclusions."
				),
				"action": "Test Execution",
			},
			{
				"number": 5,
				"title": _("Track Deficiencies"),
				"description": _("Document any control weaknesses found and track remediation to closure."),
				"action": "Deficiency",
			},
			{
				"number": 6,
				"title": _("Monitor Regulatory Updates"),
				"description": _(
					"Configure regulatory feeds to stay current with changes that may affect your controls."
				),
				"action": "Regulatory Feed Source",
			},
		],
	}
