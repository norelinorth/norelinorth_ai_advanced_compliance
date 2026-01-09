"""
Auto-Suggestions.

Intelligent suggestions for compliance actions and mappings.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, nowdate


class AutoSuggest:
	"""
	Provides intelligent suggestions for compliance operations.

	Suggestion Types:
	- Control mapping suggestions (risk to control)
	- Testing priority recommendations
	- Owner assignment suggestions
	- Remediation recommendations
	- Framework requirement mappings
	"""

	def __init__(self):
		"""Initialize auto-suggest."""
		self.settings = self._get_settings()

	def _get_settings(self):
		"""Get AI provider settings."""
		try:
			from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
				get_ai_settings,
			)

			return get_ai_settings()
		except Exception as e:
			frappe.log_error(
				message=f"Failed to load AI settings: {str(e)}\n{frappe.get_traceback()}",
				title=_("Auto Suggest Settings Error"),
			)
			return None

	def suggest_controls_for_risk(self, risk_id, limit=5):
		"""
		Suggest controls that could mitigate a risk.

		Args:
		    risk_id: Compliance Risk ID
		    limit: Maximum suggestions

		Returns:
		    List of control suggestions with scores
		"""
		if not frappe.db.exists("Risk Register Entry", risk_id):
			return []

		risk = frappe.get_doc("Risk Register Entry", risk_id)
		suggestions = []

		# Get already linked controls
		existing_controls = self._get_linked_controls(risk_id)

		# Strategy 1: Same category controls
		category_controls = frappe.get_all(
			"Control Activity",
			filters={"status": "Active", "name": ["not in", existing_controls]},
			fields=["name", "control_name", "control_type", "description"],
		)

		for control in category_controls:
			score = self._calculate_control_relevance(risk, control)
			if score > 0.3:
				suggestions.append(
					{
						"control_id": control.name,
						"control_name": control.control_name,
						"control_type": control.control_type,
						"relevance_score": round(score, 2),
						"reasoning": self._get_control_reasoning(risk, control, score),
					}
				)

		# Strategy 2: Semantic similarity (if available)
		try:
			from advanced_compliance.advanced_compliance.intelligence.search.semantic_search import (
				SemanticSearch,
			)

			search = SemanticSearch()
			search_text = f"{risk.risk_name} {risk.description or ''}"

			similar_controls = search.search(
				query=search_text, doctypes=["Control Activity"], limit=limit * 2
			)

			# Convert to sets for O(1) lookup instead of O(n)
			existing_set = set(existing_controls)
			suggestion_ids = {s["control_id"] for s in suggestions}

			for result in similar_controls:
				if result["document"] in existing_set:
					continue
				if result["document"] in suggestion_ids:
					continue

				control = frappe.get_doc("Control Activity", result["document"])
				suggestions.append(
					{
						"control_id": control.name,
						"control_name": control.control_name,
						"control_type": control.control_type,
						"relevance_score": round(result["similarity"], 2),
						"reasoning": _("Semantically similar based on description"),
					}
				)
		except Exception as e:
			frappe.log_error(
				message=f"Failed to get semantic control suggestions for risk {risk_id}: {str(e)}",
				title="Auto-Suggest Semantic Error",
			)

		# Sort by relevance
		suggestions.sort(key=lambda x: x["relevance_score"], reverse=True)
		return suggestions[:limit]

	def _get_linked_controls(self, risk_id):
		"""Get controls already linked to a risk via graph."""
		entity = frappe.db.get_value(
			"Compliance Graph Entity",
			{"entity_doctype": "Risk Register Entry", "entity_id": risk_id, "is_active": 1},
			"name",
		)

		if not entity:
			return []

		relationships = frappe.get_all(
			"Compliance Graph Relationship",
			filters={"target_entity": entity, "relationship_type": "MITIGATES", "is_active": 1},
			fields=["source_entity"],
		)

		# Bulk fetch control IDs to avoid N+1 queries
		if not relationships:
			return []

		entity_names = [rel.source_entity for rel in relationships]
		entities = frappe.get_all(
			"Compliance Graph Entity",
			filters={"name": ["in", entity_names]},
			fields=["name", "entity_id"],
		)

		# Build control_ids list from bulk query results
		control_ids = [e.entity_id for e in entities if e.entity_id]

		return control_ids

	def _calculate_control_relevance(self, risk, control):
		"""Calculate relevance score for control to risk."""
		score = 0.0

		# Type matching
		type_scores = {"Preventive": 0.4, "Detective": 0.3, "Corrective": 0.2}
		score += type_scores.get(control.control_type, 0.1)

		# Keyword matching
		risk_keywords = set((risk.risk_name or "").lower().split())
		risk_keywords.update((risk.description or "").lower().split())

		control_keywords = set((control.control_name or "").lower().split())
		control_keywords.update((control.description or "").lower().split())

		if risk_keywords and control_keywords:
			overlap = len(risk_keywords & control_keywords)
			total = len(risk_keywords | control_keywords)
			if total > 0:
				score += (overlap / total) * 0.4

		# Key control bonus
		if control.get("is_key_control"):
			score += 0.1

		return min(score, 1.0)

	def _get_control_reasoning(self, risk, control, score):
		"""Generate reasoning for control suggestion."""
		reasons = []

		if control.control_type == "Preventive":
			reasons.append(_("Preventive control can stop risk before it occurs"))
		elif control.control_type == "Detective":
			reasons.append(_("Detective control can identify risk occurrence"))

		if score > 0.7:
			reasons.append(_("High keyword overlap with risk description"))
		elif score > 0.5:
			reasons.append(_("Moderate keyword overlap with risk description"))

		return "; ".join(reasons) if reasons else _("General relevance based on control attributes")

	def suggest_testing_priority(self, limit=10):
		"""
		Suggest controls that should be prioritized for testing.

		Returns:
		    List of controls with priority scores and reasons
		"""
		suggestions = []
		today = nowdate()

		# Get active controls
		controls = frappe.get_all(
			"Control Activity",
			filters={"status": "Active"},
			fields=[
				"name",
				"control_name",
				"is_key_control",
				"last_test_date",
				"test_frequency",
				"control_type",
				"automation_level",
			],
		)

		frequency_days = {"Monthly": 30, "Quarterly": 90, "Semi-annually": 180, "Annually": 365}

		for control in controls:
			priority_score = 0.0
			reasons = []

			# Factor 1: Days since last test
			if control.last_test_date:
				days_since = date_diff(today, control.last_test_date)
				expected_days = frequency_days.get(control.test_frequency, 365)

				if days_since > expected_days:
					overdue_factor = min(days_since / expected_days, 2.0) - 1.0
					priority_score += overdue_factor * 0.4
					reasons.append(_("Overdue by {0} days").format(days_since - expected_days))
				elif days_since > expected_days * 0.8:
					priority_score += 0.2
					reasons.append(_("Testing due soon"))
			else:
				priority_score += 0.5
				reasons.append(_("Never tested"))

			# Factor 2: Key control
			if control.is_key_control:
				priority_score += 0.2
				reasons.append(_("Key control"))

			# Factor 3: Manual controls need more testing
			if control.automation_level == "Manual":
				priority_score += 0.1
				reasons.append(_("Manual control"))

			# Factor 4: Check for recent deficiencies
			recent_deficiencies = frappe.db.count(
				"Deficiency", {"control": control.name, "creation": [">=", add_days(today, -90)]}
			)
			if recent_deficiencies > 0:
				priority_score += min(recent_deficiencies * 0.1, 0.3)
				reasons.append(_("{0} recent deficiencies").format(recent_deficiencies))

			# Factor 5: Check prediction risk (if available)
			try:
				prediction = frappe.db.get_value(
					"Risk Prediction",
					{"control": control.name},
					["failure_probability", "risk_level"],
					order_by="creation desc",
					as_dict=True,
				)
				if prediction and prediction.failure_probability > 0.5:
					priority_score += flt(prediction.failure_probability) * 0.2
					reasons.append(_("High predicted risk ({0})").format(prediction.risk_level))
			except Exception as e:
				frappe.log_error(
					message=f"Failed to get risk prediction for control {control.name}: {str(e)}",
					title="Auto-Suggest Prediction Error",
				)

			if priority_score > 0.2:
				suggestions.append(
					{
						"control_id": control.name,
						"control_name": control.control_name,
						"priority_score": round(priority_score, 2),
						"reasons": reasons,
						"last_test_date": str(control.last_test_date) if control.last_test_date else None,
						"test_frequency": control.test_frequency,
					}
				)

		# Sort by priority
		suggestions.sort(key=lambda x: x["priority_score"], reverse=True)
		return suggestions[:limit]

	def suggest_owner_for_control(self, control_id, limit=3):
		"""
		Suggest appropriate owners for a control.

		Args:
		    control_id: Control Activity ID
		    limit: Maximum suggestions

		Returns:
		    List of user suggestions with scores
		"""
		if not frappe.db.exists("Control Activity", control_id):
			return []

		control = frappe.get_doc("Control Activity", control_id)
		suggestions = []

		# Get users with appropriate roles
		compliance_users = frappe.get_all(
			"Has Role",
			filters={"role": ["in", ["Compliance Manager", "Compliance User", "System Manager"]]},
			fields=["parent"],
			distinct=True,
		)

		user_ids = [u.parent for u in compliance_users]

		for user_id in user_ids:
			if not frappe.db.exists("User", user_id):
				continue

			user = frappe.get_doc("User", user_id)
			if not user.enabled:
				continue

			score = 0.0
			reasons = []

			# Factor 1: Already owns similar controls
			similar_count = frappe.db.count(
				"Control Activity",
				{"control_owner": user_id, "control_type": control.control_type, "status": "Active"},
			)
			if similar_count > 0:
				score += min(similar_count * 0.1, 0.3)
				reasons.append(_("Owns {0} similar controls").format(similar_count))

			# Factor 2: Workload (fewer controls = higher score)
			total_owned = frappe.db.count("Control Activity", {"control_owner": user_id, "status": "Active"})
			if total_owned < 5:
				score += 0.3
				reasons.append(_("Light workload ({0} controls)").format(total_owned))
			elif total_owned < 15:
				score += 0.1
				reasons.append(_("Moderate workload ({0} controls)").format(total_owned))

			# Factor 3: Has Compliance Manager role (higher authority)
			user_roles = frappe.get_roles(user_id)
			if "Compliance Manager" in user_roles:
				score += 0.2
				reasons.append(_("Compliance Manager"))

			if score > 0:
				suggestions.append(
					{
						"user_id": user_id,
						"user_name": user.full_name,
						"score": round(score, 2),
						"reasons": reasons,
						"current_control_count": total_owned,
					}
				)

		suggestions.sort(key=lambda x: x["score"], reverse=True)
		return suggestions[:limit]

	def suggest_remediation(self, deficiency_id):
		"""
		Suggest remediation steps for a deficiency.

		Args:
		    deficiency_id: Deficiency ID

		Returns:
		    Remediation suggestions
		"""
		if not frappe.db.exists("Deficiency", deficiency_id):
			return None

		deficiency = frappe.get_doc("Deficiency", deficiency_id)
		suggestions = {
			"priority": "High" if deficiency.severity in ["Significant", "Material"] else "Medium",
			"suggested_steps": [],
			"similar_remediated": [],
			"estimated_timeline": None,
		}

		# Generic steps based on severity
		severity_steps = {
			"Minor": [
				_("Document the issue and root cause"),
				_("Implement quick fix within 30 days"),
				_("Update control documentation if needed"),
			],
			"Moderate": [
				_("Perform root cause analysis"),
				_("Develop remediation plan"),
				_("Implement within 60 days"),
				_("Retest control after remediation"),
			],
			"Significant": [
				_("Escalate to management"),
				_("Perform comprehensive root cause analysis"),
				_("Develop detailed remediation plan with milestones"),
				_("Implement within 90 days"),
				_("Implement compensating controls if needed"),
				_("Schedule follow-up testing"),
			],
			"Material": [
				_("Immediate escalation to senior management"),
				_("Engage internal audit"),
				_("Implement compensating controls immediately"),
				_("Develop comprehensive remediation plan"),
				_("Weekly status reporting"),
				_("External auditor notification if required"),
			],
		}

		suggestions["suggested_steps"] = severity_steps.get(deficiency.severity, severity_steps["Moderate"])

		# Find similar remediated deficiencies
		similar = frappe.get_all(
			"Deficiency",
			filters={"severity": deficiency.severity, "status": "Closed", "name": ["!=", deficiency_id]},
			fields=["name", "title", "remediation_notes", "actual_remediation_date"],
			limit=3,
		)

		for s in similar:
			if s.remediation_notes:
				suggestions["similar_remediated"].append(
					{"deficiency": s.name, "title": s.title, "notes": s.remediation_notes[:200]}
				)

		# Timeline based on severity
		timeline_map = {
			"Minor": _("30 days"),
			"Moderate": _("60 days"),
			"Significant": _("90 days"),
			"Material": _("ASAP with interim controls"),
		}
		suggestions["estimated_timeline"] = timeline_map.get(deficiency.severity)

		return suggestions


# API Endpoints
@frappe.whitelist()
def get_control_suggestions_for_risk(risk_id, limit=5):
	"""
	API endpoint to get control suggestions for a risk.

	Args:
	    risk_id: Compliance Risk ID
	    limit: Maximum suggestions

	Returns:
	    List of control suggestions
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("auto_suggestions"):
		frappe.throw(_("Auto-suggestions are not enabled"))

	if not frappe.has_permission("Risk Register Entry", "read", risk_id):
		frappe.throw(_("No permission to access this risk"))

	suggest = AutoSuggest()
	return suggest.suggest_controls_for_risk(risk_id, cint(limit))


@frappe.whitelist()
def get_testing_priorities(limit=10):
	"""
	API endpoint to get testing priority suggestions.

	Args:
	    limit: Maximum suggestions

	Returns:
	    List of priority suggestions
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("auto_suggestions"):
		frappe.throw(_("Auto-suggestions are not enabled"))

	if not frappe.has_permission("Control Activity", "read"):
		frappe.throw(_("No permission to access controls"))

	suggest = AutoSuggest()
	return suggest.suggest_testing_priority(cint(limit))


@frappe.whitelist()
def get_owner_suggestions(control_id, limit=3):
	"""
	API endpoint to get owner suggestions for a control.

	Args:
	    control_id: Control Activity ID
	    limit: Maximum suggestions

	Returns:
	    List of user suggestions
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("auto_suggestions"):
		frappe.throw(_("Auto-suggestions are not enabled"))

	if not frappe.has_permission("Control Activity", "write", control_id):
		frappe.throw(_("No permission to modify this control"))

	suggest = AutoSuggest()
	return suggest.suggest_owner_for_control(control_id, cint(limit))


@frappe.whitelist()
def get_remediation_suggestions(deficiency_id):
	"""
	API endpoint to get remediation suggestions.

	Args:
	    deficiency_id: Deficiency ID

	Returns:
	    Remediation suggestions
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("auto_suggestions"):
		frappe.throw(_("Auto-suggestions are not enabled"))

	if not frappe.has_permission("Deficiency", "read", deficiency_id):
		frappe.throw(_("No permission to access this deficiency"))

	suggest = AutoSuggest()
	return suggest.suggest_remediation(deficiency_id)
