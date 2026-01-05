"""
COSO Principle DocType Controller

COSO (Committee of Sponsoring Organizations of the Treadway Commission)
Internal Control Framework - 17 Principles across 5 Components.
"""

import frappe
from frappe.model.document import Document


class COSOPrinciple(Document):
	"""Controller for COSO Principle DocType."""

	def validate(self):
		"""Validate COSO Principle."""
		self.validate_principle_number()

	def validate_principle_number(self):
		"""Ensure principle number is between 1 and 17."""
		if self.principle_number < 1 or self.principle_number > 17:
			frappe.throw(frappe._("COSO Principle number must be between 1 and 17"))
