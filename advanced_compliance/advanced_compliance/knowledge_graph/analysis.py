"""
Coverage Analysis Module.

Analyzes the compliance knowledge graph to identify gaps, coverage metrics,
and orphaned entities. Provides insights for compliance improvement.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt


class CoverageAnalyzer:
	"""Analyzer for compliance coverage metrics and gap identification."""

	def __init__(self):
		"""Initialize the coverage analyzer."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import GraphQueryEngine

		self.query_engine = GraphQueryEngine()

	def analyze_risk_coverage(self, company=None):
		"""
		Analyze how well risks are covered by controls.

		Args:
		    company: Optional company filter

		Returns:
		    Dict with coverage metrics and gap details
		"""
		# Get all risks
		risk_filters = {"is_active": 1, "entity_type": "Risk"}
		risks = frappe.get_all(
			"Compliance Graph Entity",
			filters=risk_filters,
			fields=["name", "entity_id", "entity_label", "properties"],
		)

		covered_risks = []
		uncovered_risks = []
		partially_covered = []

		for risk in risks:
			# Check if company filter applies
			if company:
				props = json.loads(risk.properties or "{}")
				if props.get("company") and props.get("company") != company:
					continue

			# Get mitigating controls
			mitigating = frappe.get_all(
				"Compliance Graph Relationship",
				filters={"target_entity": risk.name, "relationship_type": "MITIGATES", "is_active": 1},
				fields=["source_entity"],
			)

			control_count = len(mitigating)

			risk_info = {
				"entity": risk.name,
				"risk_id": risk.entity_id,
				"label": risk.entity_label,
				"control_count": control_count,
				"controls": [m.source_entity for m in mitigating],
			}

			if control_count == 0:
				uncovered_risks.append(risk_info)
			elif control_count == 1:
				partially_covered.append(risk_info)
			else:
				covered_risks.append(risk_info)

		total_risks = len(covered_risks) + len(uncovered_risks) + len(partially_covered)
		coverage_percentage = 0.0
		if total_risks > 0:
			coverage_percentage = flt((len(covered_risks) + len(partially_covered)) / total_risks * 100, 2)

		return {
			"total_risks": total_risks,
			"fully_covered": len(covered_risks),
			"partially_covered": len(partially_covered),
			"uncovered": len(uncovered_risks),
			"coverage_percentage": coverage_percentage,
			"uncovered_risks": uncovered_risks,
			"partially_covered_risks": partially_covered,
		}

	def analyze_control_testing(self, company=None):
		"""
		Analyze how well controls are tested.

		Args:
		    company: Optional company filter

		Returns:
		    Dict with testing coverage metrics
		"""
		# Get all controls
		control_filters = {"is_active": 1, "entity_type": "Control"}
		controls = frappe.get_all(
			"Compliance Graph Entity",
			filters=control_filters,
			fields=["name", "entity_id", "entity_label", "properties"],
		)

		tested_controls = []
		untested_controls = []
		key_controls_untested = []

		for control in controls:
			# Check company filter
			if company:
				props = json.loads(control.properties or "{}")
				if props.get("company") and props.get("company") != company:
					continue

			# Get testing evidence
			testing = frappe.get_all(
				"Compliance Graph Relationship",
				filters={"target_entity": control.name, "relationship_type": "TESTS", "is_active": 1},
				fields=["source_entity"],
			)

			props = json.loads(control.properties or "{}")
			is_key = props.get("is_key_control", False)

			control_info = {
				"entity": control.name,
				"control_id": control.entity_id,
				"label": control.entity_label,
				"is_key_control": is_key,
				"evidence_count": len(testing),
				"evidence": [t.source_entity for t in testing],
			}

			if len(testing) > 0:
				tested_controls.append(control_info)
			else:
				untested_controls.append(control_info)
				if is_key:
					key_controls_untested.append(control_info)

		total_controls = len(tested_controls) + len(untested_controls)
		testing_coverage = 0.0
		if total_controls > 0:
			testing_coverage = flt(len(tested_controls) / total_controls * 100, 2)

		return {
			"total_controls": total_controls,
			"tested": len(tested_controls),
			"untested": len(untested_controls),
			"key_controls_untested": len(key_controls_untested),
			"testing_coverage_percentage": testing_coverage,
			"untested_controls": untested_controls,
			"critical_gaps": key_controls_untested,
		}

	def analyze_ownership(self, company=None):
		"""
		Analyze control ownership coverage.

		Args:
		    company: Optional company filter

		Returns:
		    Dict with ownership metrics
		"""
		# Get all controls
		control_filters = {"is_active": 1, "entity_type": "Control"}
		controls = frappe.get_all(
			"Compliance Graph Entity",
			filters=control_filters,
			fields=["name", "entity_id", "entity_label", "properties"],
		)

		owned_controls = []
		unowned_controls = []
		owner_workload = {}

		for control in controls:
			# Check company filter
			if company:
				props = json.loads(control.properties or "{}")
				if props.get("company") and props.get("company") != company:
					continue

			# Get ownership relationships
			ownership = frappe.get_all(
				"Compliance Graph Relationship",
				filters={"target_entity": control.name, "relationship_type": "OWNS", "is_active": 1},
				fields=["source_entity"],
			)

			control_info = {
				"entity": control.name,
				"control_id": control.entity_id,
				"label": control.entity_label,
				"owner_count": len(ownership),
			}

			if len(ownership) > 0:
				owned_controls.append(control_info)
				for own in ownership:
					owner_workload[own.source_entity] = owner_workload.get(own.source_entity, 0) + 1
			else:
				unowned_controls.append(control_info)

		total_controls = len(owned_controls) + len(unowned_controls)
		ownership_coverage = 0.0
		if total_controls > 0:
			ownership_coverage = flt(len(owned_controls) / total_controls * 100, 2)

		# Convert workload to list
		workload_list = [
			{"owner": k, "control_count": v}
			for k, v in sorted(owner_workload.items(), key=lambda x: x[1], reverse=True)
		]

		return {
			"total_controls": total_controls,
			"owned": len(owned_controls),
			"unowned": len(unowned_controls),
			"ownership_coverage_percentage": ownership_coverage,
			"unowned_controls": unowned_controls,
			"owner_workload": workload_list,
		}

	def find_orphaned_entities(self):
		"""
		Find entities with no relationships.

		Returns:
		    Dict with orphaned entities by type
		"""
		orphaned = {}

		# Get all active entities
		entities = frappe.get_all(
			"Compliance Graph Entity",
			filters={"is_active": 1},
			fields=["name", "entity_type", "entity_id", "entity_label"],
		)

		for entity in entities:
			# Check for any relationships
			has_outgoing = frappe.db.exists(
				"Compliance Graph Relationship", {"source_entity": entity.name, "is_active": 1}
			)
			has_incoming = frappe.db.exists(
				"Compliance Graph Relationship", {"target_entity": entity.name, "is_active": 1}
			)

			if not has_outgoing and not has_incoming:
				entity_type = entity.entity_type
				if entity_type not in orphaned:
					orphaned[entity_type] = []

				orphaned[entity_type].append(
					{"entity": entity.name, "id": entity.entity_id, "label": entity.entity_label}
				)

		return {"orphaned_by_type": orphaned, "total_orphaned": sum(len(v) for v in orphaned.values())}

	def get_compliance_score(self, company=None):
		"""
		Calculate overall compliance score based on coverage metrics.

		Args:
		    company: Optional company filter

		Returns:
		    Dict with compliance score and breakdown
		"""
		risk_coverage = self.analyze_risk_coverage(company)
		testing_coverage = self.analyze_control_testing(company)
		ownership = self.analyze_ownership(company)

		# Weighted scoring
		weights = {"risk_coverage": 0.40, "testing_coverage": 0.35, "ownership_coverage": 0.25}

		scores = {
			"risk_coverage": risk_coverage["coverage_percentage"],
			"testing_coverage": testing_coverage["testing_coverage_percentage"],
			"ownership_coverage": ownership["ownership_coverage_percentage"],
		}

		overall_score = sum(scores[k] * weights[k] for k in weights)

		# Determine grade
		if overall_score >= 90:
			grade = "A"
		elif overall_score >= 80:
			grade = "B"
		elif overall_score >= 70:
			grade = "C"
		elif overall_score >= 60:
			grade = "D"
		else:
			grade = "F"

		return {
			"overall_score": flt(overall_score, 2),
			"grade": grade,
			"breakdown": scores,
			"weights": weights,
			"recommendations": self._get_recommendations(scores),
		}

	def _get_recommendations(self, scores):
		"""Generate recommendations based on scores."""
		recommendations = []

		if scores["risk_coverage"] < 80:
			recommendations.append(
				{
					"area": "Risk Coverage",
					"priority": "High" if scores["risk_coverage"] < 60 else "Medium",
					"recommendation": _("Review uncovered risks and assign mitigating controls"),
				}
			)

		if scores["testing_coverage"] < 80:
			recommendations.append(
				{
					"area": "Control Testing",
					"priority": "High" if scores["testing_coverage"] < 60 else "Medium",
					"recommendation": _("Establish testing procedures for untested controls"),
				}
			)

		if scores["ownership_coverage"] < 90:
			recommendations.append(
				{
					"area": "Control Ownership",
					"priority": "Medium",
					"recommendation": _("Assign owners to unowned controls"),
				}
			)

		return recommendations

	def analyze_control_dependencies(self):
		"""
		Analyze control dependency chains.

		Returns:
		    Dict with dependency analysis
		"""
		# Get all control dependency relationships
		dependencies = frappe.get_all(
			"Compliance Graph Relationship",
			filters={"relationship_type": ["in", ["DEPENDS_ON", "PRECEDED_BY"]], "is_active": 1},
			fields=["source_entity", "target_entity", "relationship_type"],
		)

		# Build dependency graph
		dependency_map = {}
		for dep in dependencies:
			source = dep.source_entity
			if source not in dependency_map:
				dependency_map[source] = []
			dependency_map[source].append({"depends_on": dep.target_entity, "type": dep.relationship_type})

		# Find critical controls (most dependents)
		dependent_count = {}
		for deps in dependency_map.values():
			for dep in deps:
				target = dep["depends_on"]
				dependent_count[target] = dependent_count.get(target, 0) + 1

		critical_controls = [
			{"entity": k, "dependent_count": v}
			for k, v in sorted(dependent_count.items(), key=lambda x: x[1], reverse=True)[:10]
		]

		# Find longest dependency chains
		max_chain_length = 0
		for control in dependency_map:
			chain_length = self._get_dependency_chain_length(control, dependency_map, set())
			max_chain_length = max(max_chain_length, chain_length)

		return {
			"total_dependencies": len(dependencies),
			"controls_with_dependencies": len(dependency_map),
			"critical_controls": critical_controls,
			"max_chain_length": max_chain_length,
		}

	def _get_dependency_chain_length(self, entity, dependency_map, visited):
		"""Recursively calculate dependency chain length."""
		if entity in visited:
			return 0  # Circular dependency

		visited.add(entity)
		max_depth = 0

		if entity in dependency_map:
			for dep in dependency_map[entity]:
				depth = self._get_dependency_chain_length(dep["depends_on"], dependency_map, visited.copy())
				max_depth = max(max_depth, depth + 1)

		return max_depth

	def get_full_analysis(self, company=None):
		"""
		Get complete coverage analysis.

		Args:
		    company: Optional company filter

		Returns:
		    Dict with all analysis results
		"""
		return {
			"compliance_score": self.get_compliance_score(company),
			"risk_coverage": self.analyze_risk_coverage(company),
			"control_testing": self.analyze_control_testing(company),
			"ownership": self.analyze_ownership(company),
			"orphaned_entities": self.find_orphaned_entities(),
			"dependencies": self.analyze_control_dependencies(),
		}


# API Endpoints
@frappe.whitelist()
def get_risk_coverage(company=None):
	"""API endpoint for risk coverage analysis."""
	if not frappe.has_permission("Compliance Graph Entity", "read"):
		frappe.throw(_("No permission to read graph entities"))

	analyzer = CoverageAnalyzer()
	return analyzer.analyze_risk_coverage(company)


@frappe.whitelist()
def get_control_testing_coverage(company=None):
	"""API endpoint for control testing coverage analysis."""
	if not frappe.has_permission("Compliance Graph Entity", "read"):
		frappe.throw(_("No permission to read graph entities"))

	analyzer = CoverageAnalyzer()
	return analyzer.analyze_control_testing(company)


@frappe.whitelist()
def get_compliance_score(company=None):
	"""API endpoint for compliance score."""
	if not frappe.has_permission("Compliance Graph Entity", "read"):
		frappe.throw(_("No permission to read graph entities"))

	analyzer = CoverageAnalyzer()
	return analyzer.get_compliance_score(company)


@frappe.whitelist()
def get_full_coverage_analysis(company=None):
	"""API endpoint for full coverage analysis."""
	if not frappe.has_permission("Compliance Graph Entity", "read"):
		frappe.throw(_("No permission to read graph entities"))

	analyzer = CoverageAnalyzer()
	return analyzer.get_full_analysis(company)


@frappe.whitelist()
def get_orphaned_entities():
	"""API endpoint for orphaned entities."""
	if not frappe.has_permission("Compliance Graph Entity", "read"):
		frappe.throw(_("No permission to read graph entities"))

	analyzer = CoverageAnalyzer()
	return analyzer.find_orphaned_entities()
