"""
Risk Register Entry DocType Controller

DocType for managing organizational risks.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class RiskRegisterEntry(Document):
	"""Controller for Risk Register Entry DocType."""

	def validate(self):
		"""Validate risk entry."""
		self.calculate_risk_scores()

	def calculate_risk_scores(self):
		"""Calculate inherent and residual risk scores."""
		# Calculate inherent risk score
		if self.inherent_likelihood and self.inherent_impact:
			likelihood = self._extract_score(self.inherent_likelihood)
			impact = self._extract_score(self.inherent_impact)
			if likelihood and impact:
				self.inherent_risk_score = likelihood * impact

		# Calculate residual risk score
		if self.residual_likelihood and self.residual_impact:
			likelihood = self._extract_score(self.residual_likelihood)
			impact = self._extract_score(self.residual_impact)
			if likelihood and impact:
				self.residual_risk_score = likelihood * impact

	def _extract_score(self, value):
		"""
		Safely extract numeric score from likelihood/impact field.

		Handles formats like:
		- "1 - Rare"
		- "3 - High"
		- Just "3"
		"""
		if not value:
			return 0
		try:
			# Try to extract number before " - " separator
			if " - " in str(value):
				return cint(str(value).split(" - ")[0])
			# Try to convert directly to int
			return cint(value)
		except (ValueError, IndexError):
			return 0

	def get_risk_level(self):
		"""Get risk level based on residual score."""
		if not self.residual_risk_score:
			return _("Unknown")

		settings = frappe.get_single("Compliance Settings")

		# Handle case where settings don't exist
		if not settings:
			frappe.throw(_("Please configure Compliance Settings before calculating risk levels"))

		critical_threshold = cint(settings.critical_risk_threshold)
		high_threshold = cint(settings.high_risk_threshold)
		# Medium threshold is optional - use .get() for safe access
		medium_threshold = cint(settings.get("medium_risk_threshold") or 0)

		if not critical_threshold or not high_threshold:
			frappe.throw(_("Please configure Risk Thresholds in Compliance Settings"))

		if self.residual_risk_score >= critical_threshold:
			return _("Critical")
		elif self.residual_risk_score >= high_threshold:
			return _("High")
		elif medium_threshold and self.residual_risk_score >= medium_threshold:
			return _("Medium")
		else:
			return _("Low")


def validate_risk(doc, method):
	"""Hook for risk validation from hooks.py."""
	pass  # Validation is handled in the class
