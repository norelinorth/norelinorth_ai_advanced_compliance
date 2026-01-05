"""
Risk Prediction DocType Controller.

Stores ML-based predictions of control failure probability.
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class RiskPrediction(Document):
	"""Controller for Risk Prediction DocType."""

	def before_insert(self):
		"""Set defaults and mark previous predictions as not current."""
		if not self.prediction_date:
			self.prediction_date = nowdate()

		# Calculate risk level if not set
		if not self.risk_level and self.failure_probability:
			self.risk_level = self.calculate_risk_level()

		# Mark previous predictions for this control as not current
		if self.is_current:
			self.mark_previous_not_current()

	def calculate_risk_level(self):
		"""Calculate risk level based on failure probability."""
		from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
			get_ai_settings,
		)

		settings = get_ai_settings()
		return settings.get_risk_level(self.failure_probability)

	def mark_previous_not_current(self):
		"""Mark previous predictions for this control as not current."""
		frappe.db.sql(
			"""
            UPDATE `tabRisk Prediction`
            SET is_current = 0
            WHERE control = %(control)s
            AND name != %(name)s
            AND is_current = 1
        """,
			{"control": self.control, "name": self.name or ""},
		)

	def get_contributing_factors_list(self):
		"""Get contributing factors as a list."""
		if not self.contributing_factors:
			return []
		try:
			return json.loads(self.contributing_factors)
		except (json.JSONDecodeError, TypeError):
			return []

	def get_recommended_actions_list(self):
		"""Get recommended actions as a list."""
		if not self.recommended_actions:
			return []
		try:
			return json.loads(self.recommended_actions)
		except (json.JSONDecodeError, TypeError):
			return []

	@staticmethod
	def create_prediction(
		control_id,
		failure_probability,
		contributing_factors=None,
		recommended_actions=None,
		model_version=None,
		confidence=None,
		feature_values=None,
		prediction_time_ms=None,
	):
		"""
		Create a new risk prediction.

		Args:
		    control_id: Control Activity ID
		    failure_probability: Predicted failure probability (0.0-1.0)
		    contributing_factors: List of factor dicts
		    recommended_actions: List of action strings
		    model_version: Model version string
		    confidence: Model confidence score
		    feature_values: Dict of feature values used
		    prediction_time_ms: Prediction time in ms

		Returns:
		    Risk Prediction document
		"""
		prediction = frappe.get_doc(
			{
				"doctype": "Risk Prediction",
				"control": control_id,
				"prediction_date": nowdate(),
				"failure_probability": flt(failure_probability, 4),
				"contributing_factors": json.dumps(contributing_factors or []),
				"recommended_actions": json.dumps(recommended_actions or []),
				"model_version": model_version,
				"confidence_score": flt(confidence, 4) if confidence else None,
				"feature_values": json.dumps(feature_values or {}),
				"prediction_time_ms": prediction_time_ms,
				"is_current": 1,
			}
		)
		prediction.insert(ignore_permissions=True)
		return prediction

	@staticmethod
	def get_current_prediction(control_id):
		"""
		Get the current (most recent) prediction for a control.

		Args:
		    control_id: Control Activity ID

		Returns:
		    Risk Prediction document or None
		"""
		name = frappe.db.get_value("Risk Prediction", {"control": control_id, "is_current": 1}, "name")
		if name:
			return frappe.get_doc("Risk Prediction", name)
		return None

	@staticmethod
	def get_high_risk_controls(threshold=None):
		"""
		Get controls with high risk predictions.

		Args:
		    threshold: Minimum failure probability (default from settings)

		Returns:
		    List of predictions
		"""
		if threshold is None:
			from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
				get_ai_settings,
			)

			settings = get_ai_settings()
			threshold = flt(settings.high_risk_threshold)
			if not threshold:
				frappe.throw(_("Please configure High Risk Threshold in AI Provider Settings"))

		return frappe.get_all(
			"Risk Prediction",
			filters={"is_current": 1, "failure_probability": [">=", threshold]},
			fields=[
				"name",
				"control",
				"control_name",
				"prediction_date",
				"failure_probability",
				"risk_level",
				"contributing_factors",
			],
			order_by="failure_probability desc",
		)

	def to_dict(self):
		"""Convert to dictionary for API response."""
		return {
			"control_id": self.control,
			"control_name": self.control_name,
			"prediction_date": str(self.prediction_date),
			"failure_probability": self.failure_probability,
			"risk_level": self.risk_level,
			"contributing_factors": self.get_contributing_factors_list(),
			"recommended_actions": self.get_recommended_actions_list(),
			"confidence": self.confidence_score,
			"is_current": self.is_current,
		}
