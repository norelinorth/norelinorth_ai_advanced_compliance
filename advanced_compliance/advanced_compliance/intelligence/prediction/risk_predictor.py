"""
Risk Predictor.

ML-based prediction of control failure likelihood using compliance data.
"""

import json
import time

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, nowdate


class RiskPredictor:
	"""
	Predicts control failure probability based on compliance features.

	Features used:
	- Test history (pass rate, days since last test)
	- Deficiency history (count, severity)
	- Control metadata (type, automation, key control)
	- Personnel (owner tenure, backup assigned)
	- Graph metrics (risk count, dependencies)
	"""

	MODEL_VERSION = "1.0.0"

	def __init__(self):
		"""Initialize the risk predictor."""
		self.model = None
		self.feature_weights = self._get_default_weights()

	def _get_default_weights(self):
		"""Get default feature weights for rule-based prediction."""
		return {
			"days_since_test": 0.15,
			"test_pass_rate": 0.20,
			"deficiency_count": 0.15,
			"deficiency_severity": 0.10,
			"is_key_control": 0.10,
			"automation_level": 0.05,
			"owner_tenure": 0.05,
			"has_backup": 0.05,
			"risk_count": 0.10,
			"testing_compliance": 0.05,
		}

	def predict(self, control_id):
		"""
		Predict failure probability for a single control.

		Args:
		    control_id: Control Activity ID

		Returns:
		    dict with prediction results
		"""
		start_time = time.time()

		# Extract features
		features = self.extract_features(control_id)

		if not features:
			return None

		# Calculate probability using rule-based approach
		# (ML model would be loaded and used here in production)
		probability = self._calculate_probability(features)

		# Get risk level
		from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
			get_ai_settings,
		)

		settings = get_ai_settings()

		# Validate settings exist before calling method
		if not settings:
			frappe.throw(_("Please configure AI Provider Settings before running risk predictions"))

		risk_level = settings.get_risk_level(probability)

		# Generate contributing factors
		contributing_factors = self._get_contributing_factors(features, probability)

		# Generate recommendations
		recommendations = self._get_recommendations(features, probability)

		prediction_time = int((time.time() - start_time) * 1000)

		return {
			"control_id": control_id,
			"failure_probability": round(probability, 4),
			"risk_level": risk_level,
			"contributing_factors": contributing_factors,
			"recommended_actions": recommendations,
			"features": features,
			"model_version": self.MODEL_VERSION,
			"prediction_time_ms": prediction_time,
		}

	def extract_features(self, control_id):
		"""
		Extract features for a control.

		Args:
		    control_id: Control Activity ID

		Returns:
		    dict of feature values
		"""
		if not frappe.db.exists("Control Activity", control_id):
			return None

		control = frappe.get_doc("Control Activity", control_id)
		today = nowdate()

		features = {
			# Test history features
			"days_since_test": self._get_days_since_test(control),
			"test_pass_rate": self._get_test_pass_rate(control_id),
			"test_count": self._get_test_count(control_id),
			"testing_compliance": self._get_testing_compliance(control),
			# Deficiency features
			"deficiency_count": self._get_deficiency_count(control_id),
			"open_deficiency_count": self._get_open_deficiency_count(control_id),
			"deficiency_severity": self._get_deficiency_severity(control_id),
			# Control metadata
			"is_key_control": 1 if control.is_key_control else 0,
			"automation_level": self._encode_automation(control.automation_level),
			"control_type": control.control_type or "Unknown",
			"frequency": control.frequency or "Unknown",
			# Personnel features
			"owner_tenure": self._get_owner_tenure(control.control_owner),
			"has_backup": 1 if control.backup_performer else 0,
			"has_performer": 1 if control.control_performer else 0,
			# Graph features
			"risk_count": self._get_risk_count(control_id),
			"dependency_count": self._get_dependency_count(control_id),
			"evidence_count": self._get_evidence_count(control_id),
		}

		return features

	def _get_days_since_test(self, control):
		"""
		Get days since last test.

		Returns:
		    int: Days since last test, or configured default for never-tested controls

		Raises:
		    frappe.ValidationError: If control never tested and no default configured
		"""
		if control.last_test_date:
			return date_diff(nowdate(), control.last_test_date)

		# Get default from Compliance Settings (no hardcoded fallback)
		settings = frappe.get_single("Compliance Settings")

		# Validate settings exist before accessing attributes
		if not settings:
			frappe.throw(_("Please configure Compliance Settings before running risk predictions"))

		default_days = cint(settings.get("default_days_never_tested"))

		if not default_days:
			frappe.throw(
				_(
					"Control {0} has never been tested and no default value is configured. Please set 'Default Days for Never-Tested Controls' in Compliance Settings."
				).format(frappe.bold(control.name))
			)

		return default_days

	def _get_test_pass_rate(self, control_id):
		"""
		Get historical test pass rate.

		Returns:
		    float: Pass rate (0.0 to 1.0) if tests exist, None if no test history
		"""
		results = frappe.db.sql(
			"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN test_result = 'Effective' THEN 1 ELSE 0 END) as passed
            FROM `tabTest Execution`
            WHERE control = %(control)s
            AND docstatus = 1
        """,
			{"control": control_id},
			as_dict=True,
		)

		if results and len(results) > 0 and results[0].total and results[0].total > 0:
			passed = results[0].passed or 0  # Handle NULL from SUM
			return passed / results[0].total

		# No test history - return None (caller will handle)
		return None

	def _get_test_count(self, control_id):
		"""Get total test count."""
		return frappe.db.count("Test Execution", {"control": control_id, "docstatus": 1})

	def _get_testing_compliance(self, control):
		"""Check if control is tested according to schedule."""
		if not control.test_frequency or not control.last_test_date:
			return 0

		frequency_days = {"Monthly": 30, "Quarterly": 90, "Semi-annually": 180, "Annually": 365}

		expected_days = frequency_days.get(control.test_frequency, 365)
		actual_days = date_diff(nowdate(), control.last_test_date)

		if actual_days <= expected_days:
			return 1.0
		elif actual_days <= expected_days * 1.5:
			return 0.5
		else:
			return 0.0

	def _get_deficiency_count(self, control_id):
		"""Get total deficiency count."""
		return frappe.db.count("Deficiency", {"control": control_id})

	def _get_open_deficiency_count(self, control_id):
		"""Get open deficiency count."""
		return frappe.db.count(
			"Deficiency", {"control": control_id, "status": ["not in", ["Closed", "Cancelled"]]}
		)

	def _get_deficiency_severity(self, control_id):
		"""Get average deficiency severity score."""
		# Severity values match Deficiency DocType options
		severity_scores = {"Control Deficiency": 1, "Significant Deficiency": 2, "Material Weakness": 3}

		deficiencies = frappe.get_all("Deficiency", filters={"control": control_id}, fields=["severity"])

		if not deficiencies:
			return 0

		total_score = sum(severity_scores.get(d.severity, 0) for d in deficiencies)
		return total_score / len(deficiencies)

	def _encode_automation(self, automation_level):
		"""Encode automation level as numeric."""
		levels = {"Fully Automated": 1.0, "Semi-automated": 0.5, "Manual": 0.0}
		return levels.get(automation_level, 0.5)

	def _get_owner_tenure(self, owner):
		"""Get control owner tenure in days."""
		if not owner:
			return 0

		creation_date = frappe.db.get_value("User", owner, "creation")
		if creation_date:
			return date_diff(nowdate(), creation_date)
		return 0

	def _get_risk_count(self, control_id):
		"""Get count of risks mitigated by this control."""
		# Check graph entity
		entity_name = frappe.db.get_value(
			"Compliance Graph Entity",
			{"entity_doctype": "Control Activity", "entity_id": control_id, "is_active": 1},
			"name",
		)

		if not entity_name:
			return 0

		return frappe.db.count(
			"Compliance Graph Relationship",
			{"source_entity": entity_name, "relationship_type": "MITIGATES", "is_active": 1},
		)

	def _get_dependency_count(self, control_id):
		"""Get count of control dependencies."""
		entity_name = frappe.db.get_value(
			"Compliance Graph Entity",
			{"entity_doctype": "Control Activity", "entity_id": control_id, "is_active": 1},
			"name",
		)

		if not entity_name:
			return 0

		return frappe.db.count(
			"Compliance Graph Relationship",
			{
				"source_entity": entity_name,
				"relationship_type": ["in", ["DEPENDS_ON", "PRECEDED_BY"]],
				"is_active": 1,
			},
		)

	def _get_evidence_count(self, control_id):
		"""Get count of evidence for this control."""
		return frappe.db.count("Control Evidence", {"control_activity": control_id})

	def _calculate_probability(self, features):
		"""
		Calculate failure probability using rule-based approach.

		In production, this would use a trained ML model.
		"""
		probability = 0.0

		# Days since test contribution (more days = higher risk)
		days_factor = min(features["days_since_test"] / 365, 1.0)
		probability += days_factor * self.feature_weights["days_since_test"]

		# Test pass rate contribution (lower rate = higher risk)
		test_pass_rate = features.get("test_pass_rate")

		if test_pass_rate is not None:
			# Has test history - use actual pass rate
			pass_rate_factor = 1.0 - test_pass_rate
			probability += pass_rate_factor * self.feature_weights["test_pass_rate"]
		else:
			# No test history - add uncertainty penalty
			# Get penalty from settings (no hardcoded fallback)
			settings = self._get_settings()

			if not settings:
				frappe.throw(_("Please configure AI Provider Settings before running risk predictions"))

			uncertainty_penalty = flt(settings.get("no_test_history_penalty"))

			if not uncertainty_penalty:
				frappe.throw(_("Please configure No Test History Penalty in AI Provider Settings"))

			probability += uncertainty_penalty

		# Deficiency contribution (more = higher risk)
		def_factor = min(features["deficiency_count"] / 5, 1.0)
		probability += def_factor * self.feature_weights["deficiency_count"]

		# Deficiency severity (higher severity = higher risk, max is 3)
		severity_factor = min(features["deficiency_severity"] / 3, 1.0)
		probability += severity_factor * self.feature_weights["deficiency_severity"]

		# Key control (key controls = higher scrutiny but not higher risk inherently)
		if features["is_key_control"]:
			probability += 0.05  # Slight increase for visibility

		# Automation (manual = higher risk)
		automation_factor = 1.0 - features["automation_level"]
		probability += automation_factor * self.feature_weights["automation_level"]

		# Backup performer (no backup = higher risk)
		if not features["has_backup"]:
			probability += self.feature_weights["has_backup"]

		# Testing compliance (non-compliant = higher risk)
		compliance_factor = 1.0 - features["testing_compliance"]
		probability += compliance_factor * self.feature_weights["testing_compliance"]

		# Open deficiencies add extra risk
		if features["open_deficiency_count"] > 0:
			probability += min(features["open_deficiency_count"] * 0.05, 0.2)

		# Ensure probability is between 0 and 1
		return max(0.0, min(1.0, probability))

	def _get_contributing_factors(self, features, probability):
		"""Get list of factors contributing to the prediction."""
		factors = []

		if features["days_since_test"] > 180:
			factors.append(
				{
					"factor": "Overdue Testing",
					"description": _("{0} days since last test").format(features["days_since_test"]),
					"impact": "high" if features["days_since_test"] > 365 else "medium",
				}
			)

		# Check test pass rate (handle None for no test history)
		test_pass_rate = features.get("test_pass_rate")
		if test_pass_rate is not None and test_pass_rate < 0.8:
			factors.append(
				{
					"factor": "Low Pass Rate",
					"description": _("{0}% historical pass rate").format(int(test_pass_rate * 100)),
					"impact": "high" if test_pass_rate < 0.5 else "medium",
				}
			)
		elif test_pass_rate is None:
			factors.append(
				{
					"factor": "No Test History",
					"description": _("Control has never been tested"),
					"impact": "medium",
				}
			)

		if features["open_deficiency_count"] > 0:
			factors.append(
				{
					"factor": "Open Deficiencies",
					"description": _("{0} unresolved deficiencies").format(features["open_deficiency_count"]),
					"impact": "high",
				}
			)

		if not features["has_backup"]:
			factors.append(
				{
					"factor": "No Backup Performer",
					"description": _("Single point of failure risk"),
					"impact": "medium",
				}
			)

		if features["automation_level"] == 0:
			factors.append(
				{
					"factor": "Manual Control",
					"description": _("Higher error probability for manual controls"),
					"impact": "low",
				}
			)

		return factors

	def _get_recommendations(self, features, probability):
		"""Get recommendations based on features."""
		recommendations = []

		if features["days_since_test"] > 90:
			recommendations.append(_("Schedule control testing immediately"))

		if features["open_deficiency_count"] > 0:
			recommendations.append(_("Remediate open deficiencies"))

		if not features["has_backup"]:
			recommendations.append(_("Assign backup performer"))

		# Check test pass rate (handle None for no test history)
		test_pass_rate = features.get("test_pass_rate")
		if test_pass_rate is not None and test_pass_rate < 0.7:
			recommendations.append(_("Review control design and operating effectiveness"))
		elif test_pass_rate is None:
			recommendations.append(_("Establish testing baseline for this control"))

		if features["automation_level"] < 0.5:
			recommendations.append(_("Consider automating this control"))

		if not recommendations:
			recommendations.append(_("Continue current monitoring"))

		return recommendations

	def predict_all(self, threshold=None):
		"""
		Predict failure probability for all active controls.

		Args:
		    threshold: Optional minimum probability to include

		Returns:
		    List of predictions
		"""
		controls = frappe.get_all("Control Activity", filters={"status": "Active"}, pluck="name")

		predictions = []
		for control_id in controls:
			prediction = self.predict(control_id)
			if prediction:
				if threshold is None or prediction["failure_probability"] >= threshold:
					predictions.append(prediction)

		# Sort by probability descending
		predictions.sort(key=lambda x: x["failure_probability"], reverse=True)

		return predictions

	def _get_settings(self):
		"""
		Get AI Provider Settings.

		Returns:
		    AI Provider Settings object or None if not configured

		Note:
		    Callers MUST check for None before using returned settings.
		"""
		try:
			from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
				get_ai_settings,
			)

			return get_ai_settings()
		except Exception:
			return None

	def save_prediction(self, prediction):
		"""
		Save a prediction to the database.

		Args:
		    prediction: Prediction dict from predict()

		Returns:
		    Risk Prediction document
		"""
		from advanced_compliance.advanced_compliance.doctype.risk_prediction.risk_prediction import (
			RiskPrediction,
		)

		return RiskPrediction.create_prediction(
			control_id=prediction["control_id"],
			failure_probability=prediction["failure_probability"],
			contributing_factors=prediction["contributing_factors"],
			recommended_actions=prediction["recommended_actions"],
			model_version=prediction["model_version"],
			confidence=0.8,  # Rule-based has fixed confidence
			feature_values=prediction["features"],
			prediction_time_ms=prediction["prediction_time_ms"],
		)


# API Endpoints
@frappe.whitelist()
def predict_control_risk(control_id):
	"""
	API endpoint to predict risk for a single control.

	Args:
	    control_id: Control Activity ID

	Returns:
	    Prediction dict
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("risk_prediction"):
		frappe.throw(_("Risk prediction is not enabled"))

	if not frappe.has_permission("Control Activity", "read", control_id):
		frappe.throw(_("No permission to access this control"))

	predictor = RiskPredictor()
	prediction = predictor.predict(control_id)

	if prediction:
		# Save prediction
		predictor.save_prediction(prediction)

	return prediction


@frappe.whitelist()
def get_high_risk_controls(threshold=None):
	"""
	API endpoint to get controls with high failure probability.

	Args:
	    threshold: Minimum probability (default from settings)

	Returns:
	    List of predictions
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("risk_prediction"):
		frappe.throw(_("Risk prediction is not enabled"))

	if not frappe.has_permission("Control Activity", "read"):
		frappe.throw(_("No permission to access controls"))

	if threshold:
		threshold = flt(threshold)

	predictor = RiskPredictor()
	return predictor.predict_all(threshold)


@frappe.whitelist()
def bulk_predict_risks():
	"""
	Run predictions for all active controls and save results.

	Returns:
	    Summary of predictions
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("risk_prediction"):
		frappe.throw(_("Risk prediction is not enabled"))

	if not frappe.has_permission("Risk Prediction", "create"):
		frappe.throw(_("No permission to create predictions"))

	predictor = RiskPredictor()
	predictions = predictor.predict_all()

	saved_count = 0
	for prediction in predictions:
		predictor.save_prediction(prediction)
		saved_count += 1

	frappe.db.commit()

	# Count by risk level
	risk_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
	for p in predictions:
		risk_counts[p["risk_level"]] = risk_counts.get(p["risk_level"], 0) + 1

	return {
		"total_predictions": saved_count,
		"by_risk_level": risk_counts,
		"high_risk_count": risk_counts.get("High", 0) + risk_counts.get("Critical", 0),
	}
