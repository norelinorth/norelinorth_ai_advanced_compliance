"""
Evidence Capture Rule DocType Controller.

Defines rules for automatic evidence capture from ERPNext documents.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class EvidenceCaptureRule(Document):
	"""Controller for Evidence Capture Rule DocType."""

	def validate(self):
		"""Validate capture rule configuration."""
		self.validate_source_doctype()
		self.validate_conditions()
		self.validate_linked_doctypes()

	def validate_source_doctype(self):
		"""Ensure source DocType is submittable if trigger is on_submit."""
		if self.trigger_event == "on_submit":
			meta = frappe.get_meta(self.source_doctype)
			if not meta.is_submittable:
				frappe.throw(
					_("Source DocType {0} is not submittable. Choose a different trigger event.").format(
						self.source_doctype
					)
				)

	def validate_conditions(self):
		"""Validate condition field names exist in source DocType."""
		if not self.conditions:
			return

		meta = frappe.get_meta(self.source_doctype)
		valid_fields = [f.fieldname for f in meta.fields]
		valid_fields.extend(["name", "owner", "creation", "modified", "docstatus"])

		for condition in self.conditions:
			if condition.field_name not in valid_fields:
				frappe.throw(
					_("Field {0} does not exist in DocType {1}").format(
						condition.field_name, self.source_doctype
					)
				)

	def validate_linked_doctypes(self):
		"""Validate linked DocTypes exist."""
		if not self.linked_doctypes:
			return

		linked_list = [dt.strip() for dt in self.linked_doctypes.split("\n") if dt.strip()]

		for doctype in linked_list:
			if not frappe.db.exists("DocType", doctype):
				frappe.throw(_("Linked DocType {0} does not exist").format(doctype))

	def get_linked_doctypes_list(self):
		"""Return linked DocTypes as a list."""
		if not self.linked_doctypes:
			return []
		return [dt.strip() for dt in self.linked_doctypes.split("\n") if dt.strip()]
