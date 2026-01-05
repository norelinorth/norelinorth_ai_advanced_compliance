"""
Test Execution DocType Controller

DocType for recording control test executions.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class TestExecution(Document):
	"""Controller for Test Execution DocType."""

	def validate(self):
		"""Validate test execution."""
		self.validate_result_requires_conclusion()

	def validate_result_requires_conclusion(self):
		"""Ineffective results require conclusion."""
		if self.test_result and "Ineffective" in self.test_result:
			if not self.conclusion:
				frappe.throw(_("Conclusion is required when test result is Ineffective"))

	def on_submit(self):
		"""Actions on test submission."""
		self.update_control_test_info()
		self.create_deficiency_if_needed()

	def before_cancel(self):
		"""Actions before test cancellation."""
		pass  # Can add cancellation logic here

	def update_control_test_info(self):
		"""Update the linked control with test information."""
		if self.control and frappe.db.exists("Control Activity", self.control):
			control = frappe.get_doc("Control Activity", self.control)
			control.update_test_info(self.test_date, self.test_result)

	def create_deficiency_if_needed(self):
		"""Auto-create deficiency for failed tests if configured."""
		if not self.test_result or "Ineffective" not in self.test_result:
			return

		settings = frappe.get_single("Compliance Settings")
		if not settings or not settings.auto_create_deficiency:
			return

		# Determine severity from test result
		severity_map = {
			"Ineffective - Minor": "Control Deficiency",
			"Ineffective - Significant": "Significant Deficiency",
			"Ineffective - Material": "Material Weakness",
		}
		severity = severity_map.get(self.test_result, "Control Deficiency")

		deficiency = frappe.get_doc(
			{
				"doctype": "Deficiency",
				"control": self.control,
				"test_execution": self.name,
				"severity": severity,
				"description": self.conclusion or _("Deficiency identified during testing"),
				"status": "Open",
				"identified_date": self.test_date,
				"identified_by": self.tester,
			}
		)
		deficiency.insert(ignore_permissions=True)
		frappe.msgprint(_("Deficiency {0} created automatically").format(deficiency.name), indicator="orange")


def validate_test(doc, method):
	"""Hook for test validation from hooks.py."""
	pass


def on_submit(doc, method):
	"""Hook for test submission from hooks.py."""
	pass


def before_cancel(doc, method):
	"""Hook for test cancellation from hooks.py."""
	pass
