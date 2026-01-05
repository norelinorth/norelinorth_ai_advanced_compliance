"""
Compliance Settings DocType Controller

Single DocType for app-wide configuration.
"""

import frappe
from frappe.model.document import Document


class ComplianceSettings(Document):
	"""Controller for Compliance Settings DocType."""

	def validate(self):
		"""Validate settings."""
		self.validate_thresholds()

	def validate_thresholds(self):
		"""Ensure high risk threshold is less than critical threshold."""
		if self.high_risk_threshold and self.critical_risk_threshold:
			if self.high_risk_threshold >= self.critical_risk_threshold:
				frappe.throw(frappe._("High Risk Threshold must be less than Critical Risk Threshold"))
