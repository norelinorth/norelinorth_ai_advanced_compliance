"""
Automatic Evidence Capture Engine.

Captures document evidence when ERPNext transactions are submitted.
Follows standard Frappe patterns for document hooks.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime


def on_document_submit(doc, method):
	"""
	Hook called when documents are submitted.

	Evaluates capture rules and captures evidence.

	Args:
	    doc: The submitted document
	    method: The hook method name
	"""
	# Check if compliance features are enabled
	settings = frappe.get_single("Compliance Settings")
	if not settings or not settings.enable_compliance_features:
		return

	# Get applicable capture rules
	rules = get_applicable_rules(doc.doctype, "on_submit")

	if not rules:
		return

	for rule in rules:
		if evaluate_conditions(doc, rule):
			try:
				capture_evidence(doc, rule)
			except Exception as e:
				# Log error but don't fail the transaction
				frappe.log_error(
					message=f"Evidence capture failed for {doc.doctype} {doc.name}: {str(e)}",
					title=_("Evidence Capture Error"),
				)


def on_document_update(doc, method):
	"""
	Hook called when documents are updated.

	Args:
	    doc: The updated document
	    method: The hook method name
	"""
	settings = frappe.get_single("Compliance Settings")
	if not settings or not settings.enable_compliance_features:
		return

	rules = get_applicable_rules(doc.doctype, "on_update")

	if not rules:
		return

	for rule in rules:
		if evaluate_conditions(doc, rule):
			try:
				capture_evidence(doc, rule)
			except Exception as e:
				frappe.log_error(
					message=f"Evidence capture failed for {doc.doctype} {doc.name}: {str(e)}",
					title=_("Evidence Capture Error"),
				)


def on_document_cancel(doc, method):
	"""
	Hook called when documents are cancelled.

	Args:
	    doc: The cancelled document
	    method: The hook method name
	"""
	settings = frappe.get_single("Compliance Settings")
	if not settings or not settings.enable_compliance_features:
		return

	rules = get_applicable_rules(doc.doctype, "on_cancel")

	if not rules:
		return

	for rule in rules:
		if evaluate_conditions(doc, rule):
			try:
				capture_evidence(doc, rule)
			except Exception as e:
				frappe.log_error(
					message=f"Evidence capture failed for {doc.doctype} {doc.name}: {str(e)}",
					title=_("Evidence Capture Error"),
				)


def get_applicable_rules(doctype, trigger_event):
	"""
	Get capture rules for this document type and trigger event.

	Args:
	    doctype: The DocType name
	    trigger_event: The event trigger (on_submit, on_update, on_cancel)

	Returns:
	    List of Evidence Capture Rule documents
	"""
	return frappe.get_all(
		"Evidence Capture Rule",
		filters={"source_doctype": doctype, "trigger_event": trigger_event, "enabled": 1},
		fields=[
			"name",
			"rule_name",
			"control_activity",
			"source_doctype",
			"capture_document_pdf",
			"capture_workflow_history",
			"capture_version_history",
			"capture_comments",
			"linked_doctypes",
		],
	)


def evaluate_conditions(doc, rule):
	"""
	Evaluate if document meets rule conditions.

	Args:
	    doc: The document to evaluate
	    rule: The capture rule

	Returns:
	    True if all conditions are met, False otherwise
	"""
	conditions = frappe.get_all(
		"Evidence Capture Condition",
		filters={"parent": rule.name},
		fields=["field_name", "operator", "value"],
	)

	if not conditions:
		# No conditions means capture all documents of this type
		return True

	for condition in conditions:
		field_value = doc.get(condition.field_name)

		if not evaluate_single_condition(field_value, condition.operator, condition.value):
			return False

	return True


def evaluate_single_condition(field_value, operator, check_value):
	"""
	Evaluate a single condition.

	Args:
	    field_value: The actual field value from the document
	    operator: The comparison operator
	    check_value: The value to compare against

	Returns:
	    True if condition is met, False otherwise
	"""
	# Handle None values
	if field_value is None:
		field_value = ""

	# Convert check_value to appropriate type based on field_value
	if isinstance(field_value, int | float):
		try:
			check_value = flt(check_value)
		except (ValueError, TypeError):
			return False

	operators = {
		"=": lambda a, b: str(a) == str(b),
		"!=": lambda a, b: str(a) != str(b),
		">": lambda a, b: flt(a) > flt(b),
		">=": lambda a, b: flt(a) >= flt(b),
		"<": lambda a, b: flt(a) < flt(b),
		"<=": lambda a, b: flt(a) <= flt(b),
		"in": lambda a, b: str(a) in [v.strip() for v in str(b).split(",")],
		"not in": lambda a, b: str(a) not in [v.strip() for v in str(b).split(",")],
	}

	evaluator = operators.get(operator)
	if not evaluator:
		return False

	try:
		return evaluator(field_value, check_value)
	except (ValueError, TypeError):
		return False


def capture_evidence(doc, rule):
	"""
	Capture evidence for a document based on rule configuration.

	Args:
	    doc: The document to capture evidence from
	    rule: The capture rule configuration
	"""
	evidence = frappe.new_doc("Control Evidence")
	evidence.control_activity = rule.control_activity
	evidence.capture_rule = rule.name
	evidence.source_doctype = doc.doctype
	evidence.source_name = doc.name
	evidence.source_owner = doc.owner
	evidence.captured_at = now_datetime()

	# Get company if available
	if hasattr(doc, "company"):
		evidence.source_company = doc.company

	# Capture document PDF snapshot
	if rule.capture_document_pdf:
		evidence.document_snapshot = capture_document_pdf(doc)

	# Capture workflow history
	if rule.capture_workflow_history:
		evidence.workflow_log = capture_workflow_history(doc)

	# Capture version history
	if rule.capture_version_history:
		evidence.version_history = capture_version_history(doc)

	# Capture comments
	if rule.capture_comments:
		evidence.comments_log = capture_comments(doc)

	# Capture linked documents
	if rule.linked_doctypes:
		linked_doctypes = [dt.strip() for dt in rule.linked_doctypes.split("\n") if dt.strip()]
		capture_linked_documents(evidence, doc, linked_doctypes)

	# Validate user has permission to create Control Evidence
	# Evidence capture is an audit function that should respect user permissions
	if not frappe.has_permission("Control Evidence", "create"):
		frappe.throw(
			_("Evidence capture failed: You do not have permission to create Control Evidence records."),
			frappe.PermissionError,
		)

	evidence.insert()

	frappe.logger("compliance").info(f"Evidence captured: {evidence.name} for {doc.doctype} {doc.name}")

	return evidence


def capture_document_pdf(doc):
	"""
	Generate PDF snapshot of document.

	Args:
	    doc: The document to capture

	Returns:
	    File URL of the captured PDF, or None if failed
	"""
	try:
		from frappe.utils.pdf import get_pdf

		# Get print format
		print_format = get_default_print_format(doc.doctype)

		html = frappe.get_print(doc.doctype, doc.name, print_format=print_format)

		# Generate PDF
		pdf_content = get_pdf(html)

		# Create unique filename
		timestamp = now_datetime().strftime("%Y%m%d_%H%M%S")
		file_name = f"evidence_{doc.doctype}_{doc.name}_{timestamp}.pdf"

		# Save file
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": file_name,
				"content": pdf_content,
				"is_private": 1,
				"folder": "Home/Compliance Evidence",
			}
		)
		# Permission check is handled by parent capture_evidence() function
		file_doc.insert()

		return file_doc.file_url

	except Exception as e:
		frappe.log_error(
			message=f"Failed to capture PDF for {doc.doctype} {doc.name}: {str(e)}",
			title=_("PDF Capture Error"),
		)
		return None


def get_default_print_format(doctype):
	"""
	Get default print format for DocType.

	Args:
	    doctype: The DocType name

	Returns:
	    Print format name or "Standard"
	"""
	default = frappe.db.get_value(
		"Property Setter", {"doc_type": doctype, "property": "default_print_format"}, "value"
	)
	return default or "Standard"


def capture_workflow_history(doc):
	"""
	Capture workflow actions and approvals.

	Args:
	    doc: The document

	Returns:
	    JSON string of workflow history
	"""
	workflow_logs = []

	# Get workflow actions
	actions = frappe.get_all(
		"Workflow Action Log",
		filters={"reference_doctype": doc.doctype, "reference_name": doc.name},
		fields=["action", "user", "creation", "comment"],
		order_by="creation asc",
	)

	for action in actions:
		workflow_logs.append(
			{
				"type": "workflow_action",
				"action": action.action,
				"user": action.user,
				"timestamp": str(action.creation),
				"comment": action.comment,
			}
		)

	# Get submission/cancellation info from comments
	submit_comments = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"comment_type": ["in", ["Submitted", "Cancelled"]],
		},
		fields=["comment_type", "owner", "creation"],
		order_by="creation asc",
	)

	for comment in submit_comments:
		workflow_logs.append(
			{
				"type": "submission",
				"action": comment.comment_type,
				"user": comment.owner,
				"timestamp": str(comment.creation),
			}
		)

	return json.dumps(workflow_logs, indent=2) if workflow_logs else None


def capture_version_history(doc):
	"""
	Capture all changes made to document.

	Args:
	    doc: The document

	Returns:
	    JSON string of version history
	"""
	versions = frappe.get_all(
		"Version",
		filters={"ref_doctype": doc.doctype, "docname": doc.name},
		fields=["owner", "creation", "data"],
		order_by="creation asc",
	)

	version_log = []
	for version in versions:
		# Truncate large version data with warning
		changes_data = version.data
		if version.data and len(version.data) > 5000:
			changes_data = version.data[:5000]
			frappe.logger("compliance").warning(
				f"Version history truncated for {doc.doctype} {doc.name}: "
				f"Original size {len(version.data)} chars, truncated to 5000 chars"
			)

		version_log.append(
			{
				"user": version.owner,
				"timestamp": str(version.creation),
				"changes": changes_data,
			}
		)

	return json.dumps(version_log, indent=2) if version_log else None


def capture_comments(doc):
	"""
	Capture document comments.

	Args:
	    doc: The document

	Returns:
	    JSON string of comments
	"""
	comments = frappe.get_all(
		"Comment",
		filters={"reference_doctype": doc.doctype, "reference_name": doc.name, "comment_type": "Comment"},
		fields=["owner", "creation", "content"],
		order_by="creation asc",
	)

	comments_log = []
	for comment in comments:
		# Truncate large comment content with warning
		content_data = comment.content
		if comment.content and len(comment.content) > 2000:
			content_data = comment.content[:2000]
			frappe.logger("compliance").warning(
				f"Comment content truncated for {doc.doctype} {doc.name}: "
				f"Original size {len(comment.content)} chars, truncated to 2000 chars"
			)

		comments_log.append(
			{
				"user": comment.owner,
				"timestamp": str(comment.creation),
				"content": content_data,
			}
		)

	return json.dumps(comments_log, indent=2) if comments_log else None


def capture_linked_documents(evidence, doc, linked_doctypes):
	"""
	Capture references to linked documents.

	Args:
	    evidence: The Control Evidence document
	    doc: The source document
	    linked_doctypes: List of DocTypes to find links for
	"""
	for link_doctype in linked_doctypes:
		linked_docs = find_linked_documents(doc, link_doctype)

		for linked_doc in linked_docs:
			evidence.append(
				"linked_documents",
				{
					"document_type": link_doctype,
					"document_name": linked_doc.get("name"),
					"link_field": linked_doc.get("link_field", ""),
				},
			)


def find_linked_documents(doc, link_doctype):
	"""
	Find documents linked to the source document.

	Args:
	    doc: The source document
	    link_doctype: The DocType to find links for

	Returns:
	    List of linked document references
	"""
	linked = []

	# Check for direct link fields in source document
	meta = frappe.get_meta(doc.doctype)
	for field in meta.get_link_fields():
		if field.options == link_doctype:
			value = doc.get(field.fieldname)
			if value:
				linked.append({"name": value, "link_field": field.fieldname})

	# Check for references in the linked DocType pointing to source
	try:
		link_meta = frappe.get_meta(link_doctype)
		for field in link_meta.get_link_fields():
			if field.options == doc.doctype:
				refs = frappe.get_all(
					link_doctype,
					filters={field.fieldname: doc.name},
					pluck="name",
					limit=50,  # Limit to prevent too many links
				)
				for ref in refs:
					if {"name": ref, "link_field": field.fieldname} not in linked:
						linked.append({"name": ref, "link_field": field.fieldname})
	except Exception:
		# DocType might not exist or have issues
		pass

	return linked


@frappe.whitelist()
def manually_capture_evidence(doctype, docname, control_activity):
	"""
	Manually capture evidence for a document.

	API endpoint for manual evidence capture.

	Args:
	    doctype: Document type
	    docname: Document name
	    control_activity: Control Activity to link evidence to

	Returns:
	    Control Evidence document name
	"""
	if not frappe.has_permission("Control Evidence", "create"):
		frappe.throw(_("No permission to create Control Evidence"))

	# Validate document exists
	if not frappe.db.exists(doctype, docname):
		frappe.throw(_("{0} {1} does not exist").format(frappe.bold(doctype), frappe.bold(docname)))

	doc = frappe.get_doc(doctype, docname)

	evidence = frappe.new_doc("Control Evidence")
	evidence.control_activity = control_activity
	evidence.source_doctype = doctype
	evidence.source_name = docname
	evidence.source_owner = doc.owner
	evidence.captured_at = now_datetime()

	if hasattr(doc, "company"):
		evidence.source_company = doc.company

	# Capture all available evidence
	evidence.document_snapshot = capture_document_pdf(doc)
	evidence.workflow_log = capture_workflow_history(doc)
	evidence.version_history = capture_version_history(doc)
	evidence.comments_log = capture_comments(doc)

	evidence.insert()

	return evidence.name
