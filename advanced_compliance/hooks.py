app_name = "advanced_compliance"
app_title = "Noreli North AI Advanced Compliance"
app_publisher = "Noreli North"
app_description = "Next-generation GRC with Knowledge Graph and AI Intelligence for ERPNext"
app_email = ""
app_license = "MIT"
app_version = "1.1.1"

# Required Apps
required_apps = ["frappe", "erpnext"]

# App Includes
# --------------------

# CSS to include in desk
app_include_css = "/assets/advanced_compliance/css/advanced_compliance.css"

# JS to include in desk
app_include_js = "/assets/advanced_compliance/js/advanced_compliance.js"

# Installation
# --------------------
before_install = "advanced_compliance.install.before_install"
after_install = "advanced_compliance.install.after_install"
after_uninstall = "advanced_compliance.uninstall.after_uninstall"

# Migration
after_migrate = "advanced_compliance.install.after_migrate"

# Fixtures
# --------------------
fixtures = [
	# Export workspace
	{"dt": "Workspace", "filters": [["module", "=", "Advanced Compliance"]]},
	# Export custom roles
	{
		"dt": "Role",
		"filters": [
			[
				"name",
				"in",
				[
					"Compliance Admin",
					"Compliance Officer",
					"Internal Auditor",
					"Control Owner",
					"Compliance Viewer",
				],
			]
		],
	},
	# Export base compliance master data
	{"dt": "COSO Principle"},
	{"dt": "Control Category"},
	{"dt": "Risk Category"},
	# Export regulatory feed sources (configuration)
	{"dt": "Regulatory Feed Source"},
	# Export evidence capture rules (configuration)
	{"dt": "Evidence Capture Rule"},
]

# Document Events
# --------------------
doc_events = {
	# Control Activity lifecycle
	"Control Activity": {
		"validate": "advanced_compliance.advanced_compliance.doctype.control_activity.control_activity.validate_control",
		"after_insert": "advanced_compliance.advanced_compliance.knowledge_graph.sync.on_control_created",
		"on_update": "advanced_compliance.advanced_compliance.knowledge_graph.sync.on_control_updated",
		"on_trash": "advanced_compliance.advanced_compliance.knowledge_graph.sync.on_control_deleted",
	},
	# Risk Register Entry lifecycle
	"Risk Register Entry": {
		"validate": "advanced_compliance.advanced_compliance.doctype.risk_register_entry.risk_register_entry.validate_risk",
		"after_insert": "advanced_compliance.advanced_compliance.knowledge_graph.sync.on_risk_created",
		"on_update": "advanced_compliance.advanced_compliance.knowledge_graph.sync.on_risk_updated",
	},
	# Control Evidence lifecycle (graph sync)
	"Control Evidence": {
		"after_insert": "advanced_compliance.advanced_compliance.knowledge_graph.sync.on_evidence_created"
	},
	# Test Execution lifecycle (with graph sync)
	"Test Execution": {
		"validate": "advanced_compliance.advanced_compliance.doctype.test_execution.test_execution.validate_test",
		"on_submit": "advanced_compliance.advanced_compliance.doctype.test_execution.test_execution.on_submit",
		"before_cancel": "advanced_compliance.advanced_compliance.doctype.test_execution.test_execution.before_cancel",
		"after_insert": "advanced_compliance.advanced_compliance.knowledge_graph.sync.on_test_created",
		"on_update": "advanced_compliance.advanced_compliance.knowledge_graph.sync.on_test_updated",
	},
	# Deficiency workflow
	"Deficiency": {
		"validate": "advanced_compliance.advanced_compliance.doctype.deficiency.deficiency.validate_deficiency",
		"on_update": "advanced_compliance.advanced_compliance.doctype.deficiency.deficiency.on_update",
	},
	# Evidence Capture - ERPNext Transaction Documents
	"Sales Invoice": {
		"on_submit": "advanced_compliance.advanced_compliance.evidence.capture.on_document_submit",
		"on_cancel": "advanced_compliance.advanced_compliance.evidence.capture.on_document_cancel",
	},
	"Purchase Invoice": {
		"on_submit": "advanced_compliance.advanced_compliance.evidence.capture.on_document_submit",
		"on_cancel": "advanced_compliance.advanced_compliance.evidence.capture.on_document_cancel",
	},
	"Journal Entry": {
		"on_submit": "advanced_compliance.advanced_compliance.evidence.capture.on_document_submit",
		"on_cancel": "advanced_compliance.advanced_compliance.evidence.capture.on_document_cancel",
	},
	"Payment Entry": {
		"on_submit": "advanced_compliance.advanced_compliance.evidence.capture.on_document_submit",
		"on_cancel": "advanced_compliance.advanced_compliance.evidence.capture.on_document_cancel",
	},
	"Purchase Order": {
		"on_submit": "advanced_compliance.advanced_compliance.evidence.capture.on_document_submit",
		"on_cancel": "advanced_compliance.advanced_compliance.evidence.capture.on_document_cancel",
	},
	"Sales Order": {
		"on_submit": "advanced_compliance.advanced_compliance.evidence.capture.on_document_submit",
		"on_cancel": "advanced_compliance.advanced_compliance.evidence.capture.on_document_cancel",
	},
	"Stock Entry": {
		"on_submit": "advanced_compliance.advanced_compliance.evidence.capture.on_document_submit",
		"on_cancel": "advanced_compliance.advanced_compliance.evidence.capture.on_document_cancel",
	},
}

# Scheduled Tasks
# --------------------
scheduler_events = {
	"hourly": [
		# Regulatory Feeds - High priority feed sync
		"advanced_compliance.advanced_compliance.regulatory_feeds.scheduler.sync_high_priority_feeds"
	],
	"daily": [
		"advanced_compliance.advanced_compliance.tasks.daily.check_overdue_tests",
		"advanced_compliance.advanced_compliance.tasks.daily.send_control_owner_reminders",
		# Regulatory Feeds - Daily sync and analysis
		"advanced_compliance.advanced_compliance.regulatory_feeds.scheduler.sync_all_feeds",
		"advanced_compliance.advanced_compliance.regulatory_feeds.scheduler.detect_upcoming_deadlines",
	],
	"weekly": [
		"advanced_compliance.advanced_compliance.tasks.weekly.generate_compliance_digest",
		# Regulatory Feeds - Weekly digest
		"advanced_compliance.advanced_compliance.regulatory_feeds.scheduler.generate_regulatory_digest",
	],
	"monthly": [
		"advanced_compliance.advanced_compliance.tasks.monthly.calculate_compliance_scores",
		# Regulatory Feeds - Cleanup old updates
		"advanced_compliance.advanced_compliance.regulatory_feeds.scheduler.cleanup_old_updates",
	],
}

# Permissions
# --------------------
permission_query_conditions = {
	"Control Activity": "advanced_compliance.advanced_compliance.permissions.control_activity_query",
	"Risk Register Entry": "advanced_compliance.advanced_compliance.permissions.risk_entry_query",
	"Test Execution": "advanced_compliance.advanced_compliance.permissions.test_execution_query",
	"Deficiency": "advanced_compliance.advanced_compliance.permissions.deficiency_query",
}

has_permission = {
	"Control Activity": "advanced_compliance.advanced_compliance.permissions.control_activity_permission",
	"Test Execution": "advanced_compliance.advanced_compliance.permissions.test_execution_permission",
}

# User Data Protection (GDPR)
user_data_fields = [
	{"doctype": "Control Activity", "filter_by": "control_owner", "redact_fields": [], "partial": True},
	{"doctype": "Test Execution", "filter_by": "tester", "redact_fields": [], "partial": True},
]
