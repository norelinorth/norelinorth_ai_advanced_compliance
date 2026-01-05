"""
Control Activity DocType Controller

Main DocType for managing internal controls in the compliance framework.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, getdate


class ControlActivity(Document):
	"""Controller for Control Activity DocType."""

	def onload(self):
		"""Load AI prediction data when document is opened."""
		self.load_ai_prediction()

	def load_ai_prediction(self):
		"""Fetch current Risk Prediction for this control."""
		prediction = frappe.db.get_value(
			"Risk Prediction",
			filters={"control": self.name, "is_current": 1},
			fieldname=["name", "failure_probability", "risk_level", "prediction_date"],
			as_dict=True,
		)

		if prediction:
			# Convert probability to percentage (0.15 -> 15)
			self.ai_failure_probability = (prediction.failure_probability or 0) * 100
			self.ai_risk_level = prediction.risk_level
			self.ai_prediction_date = prediction.prediction_date
			self.ai_prediction_link = prediction.name

	def validate(self):
		"""Validate control activity."""
		self.validate_key_control()
		self.validate_coso_mapping()
		self.calculate_next_test_date()

	def validate_key_control(self):
		"""Key controls must have test frequency defined."""
		if self.is_key_control and not self.test_frequency:
			frappe.throw(_("Key Controls must have a Test Frequency defined"))

	def validate_coso_mapping(self):
		"""If COSO principle is set, component should match."""
		if self.coso_principle and self.coso_component:
			# Verify COSO Principle exists before loading
			if not frappe.db.exists("COSO Principle", self.coso_principle):
				frappe.throw(_("COSO Principle {0} does not exist").format(frappe.bold(self.coso_principle)))

			principle = frappe.get_doc("COSO Principle", self.coso_principle)
			if principle.component != self.coso_component:
				frappe.throw(
					_("COSO Principle {0} belongs to component '{1}', not '{2}'").format(
						self.coso_principle, principle.component, self.coso_component
					)
				)

	def calculate_next_test_date(self):
		"""Calculate next test date based on frequency and last test."""
		if not self.test_frequency or not self.last_test_date:
			return

		frequency_months = {"Monthly": 1, "Quarterly": 3, "Semi-annually": 6, "Annually": 12}

		months = frequency_months.get(self.test_frequency)
		if months:
			self.next_test_date = add_months(getdate(self.last_test_date), months)

	def update_test_info(self, test_date, test_result):
		"""Update testing information from Test Execution."""
		self.last_test_date = test_date
		self.last_test_result = test_result
		self.calculate_next_test_date()
		self.save(ignore_permissions=True)

	def on_update(self):
		"""After save, propagate changes to linked documents."""
		self.update_linked_risk_entries()

	def update_linked_risk_entries(self):
		"""Update last_test_result in Risk Register Entry mitigating controls.

		The fetch_from property only works at creation/link change,
		so we need to manually propagate updates to the source field.
		"""
		# Find all Risk Control Link rows that reference this control
		linked_rows = frappe.db.get_all(
			"Risk Control Link", filters={"control": self.name}, fields=["name", "parent"]
		)

		if not linked_rows:
			return

		for row in linked_rows:
			# Update the child table row directly
			frappe.db.set_value(
				"Risk Control Link",
				row.name,
				"last_test_result",
				self.last_test_result,
				update_modified=False,
			)

		# Update modified timestamp on parent documents
		parent_names = list(set(row.parent for row in linked_rows))
		for parent in parent_names:
			frappe.db.set_value(
				"Risk Register Entry", parent, "modified", frappe.utils.now(), update_modified=False
			)


def validate_control(doc, method):
	"""Hook for control validation from hooks.py."""
	pass  # Validation is handled in the class
