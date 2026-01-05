"""
Deficiency DocType Controller

DocType for tracking control deficiencies and remediation.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class Deficiency(Document):
	"""Controller for Deficiency DocType."""

	def validate(self):
		"""Validate deficiency."""
		self.validate_closure()
		self.validate_dates()

	def validate_closure(self):
		"""Closure requires notes and date."""
		if self.status == "Closed":
			if not self.closure_date:
				self.closure_date = nowdate()
			if not self.closure_notes:
				frappe.throw(_("Closure Notes are required when closing a deficiency"))

	def validate_dates(self):
		"""Target date should be after identified date."""
		if self.target_date and self.identified_date:
			if getdate(self.target_date) < getdate(self.identified_date):
				frappe.throw(_("Target Remediation Date cannot be before Identified Date"))

	def on_update(self):
		"""Actions on deficiency update."""
		self.notify_if_overdue()

	def notify_if_overdue(self):
		"""Send notification if deficiency is overdue."""
		if self.status in ["Open", "In Progress"] and self.target_date:
			if getdate(self.target_date) < getdate(nowdate()):
				# Could trigger notification here
				pass


def validate_deficiency(doc, method):
	"""Hook for deficiency validation from hooks.py."""
	pass


def on_update(doc, method):
	"""Hook for deficiency update from hooks.py."""
	pass
