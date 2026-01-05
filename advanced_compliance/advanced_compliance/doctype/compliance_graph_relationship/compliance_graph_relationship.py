"""
Compliance Graph Relationship DocType Controller.

Represents an edge in the compliance knowledge graph.
Connects two Compliance Graph Entity nodes with a typed relationship.
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

# Relationship type definitions with allowed source/target entity types
RELATIONSHIP_DEFINITIONS = {
	"MITIGATES": {
		"description": "Control mitigates a risk",
		"source_types": ["Control"],
		"target_types": ["Risk"],
		"edge_color": "#27ae60",
	},
	"OWNS": {
		"description": "Person owns a control or risk",
		"source_types": ["Person"],
		"target_types": ["Control", "Risk"],
		"edge_color": "#3498db",
	},
	"PERFORMS": {
		"description": "Person performs a control",
		"source_types": ["Person"],
		"target_types": ["Control"],
		"edge_color": "#9b59b6",
	},
	"TESTS": {
		"description": "Evidence tests a control",
		"source_types": ["Evidence"],
		"target_types": ["Control"],
		"edge_color": "#f39c12",
	},
	"EXECUTES": {
		"description": "Person executes a test",
		"source_types": ["Person"],
		"target_types": ["Evidence"],
		"edge_color": "#8e44ad",
	},
	"SUPPORTS": {
		"description": "Control supports a process",
		"source_types": ["Control"],
		"target_types": ["Process"],
		"edge_color": "#2ecc71",
	},
	"DEPENDS_ON": {
		"description": "Control depends on another control",
		"source_types": ["Control"],
		"target_types": ["Control"],
		"edge_color": "#e74c3c",
	},
	"ADDRESSES": {
		"description": "Control addresses an objective",
		"source_types": ["Control"],
		"target_types": ["Objective"],
		"edge_color": "#1abc9c",
	},
	"REQUIRES": {
		"description": "Regulation requires a requirement",
		"source_types": ["Requirement"],
		"target_types": ["Objective", "Control"],
		"edge_color": "#34495e",
	},
	"MANDATES": {
		"description": "Requirement mandates an objective",
		"source_types": ["Requirement"],
		"target_types": ["Objective"],
		"edge_color": "#16a085",
	},
	"MANAGES": {
		"description": "Person manages a process",
		"source_types": ["Person"],
		"target_types": ["Process"],
		"edge_color": "#8e44ad",
	},
	"OPERATES": {
		"description": "Department operates a system",
		"source_types": ["Department"],
		"target_types": ["System"],
		"edge_color": "#95a5a6",
	},
	"BELONGS_TO": {
		"description": "Entity belongs to a company or department",
		"source_types": ["Person", "Control", "Risk", "Evidence"],
		"target_types": ["Department", "Company"],
		"edge_color": "#e67e22",
	},
	"USES": {
		"description": "Process uses a system",
		"source_types": ["Process"],
		"target_types": ["System"],
		"edge_color": "#7f8c8d",
	},
	"PRECEDED_BY": {
		"description": "Control is preceded by another control",
		"source_types": ["Control"],
		"target_types": ["Control"],
		"edge_color": "#bdc3c7",
	},
	"OCCURRED_IN": {
		"description": "Evidence occurred in a period",
		"source_types": ["Evidence"],
		"target_types": ["Period"],
		"edge_color": "#d35400",
	},
	"EFFECTIVE_FROM": {
		"description": "Control effective from a period",
		"source_types": ["Control"],
		"target_types": ["Period"],
		"edge_color": "#c0392b",
	},
	"SUPERSEDES": {
		"description": "Requirement supersedes another",
		"source_types": ["Requirement"],
		"target_types": ["Requirement"],
		"edge_color": "#2c3e50",
	},
	"AFFECTS": {
		"description": "Risk affects a process",
		"source_types": ["Risk"],
		"target_types": ["Process"],
		"edge_color": "#e74c3c",
	},
	"IMPACTS": {
		"description": "Deficiency impacts a control",
		"source_types": ["Evidence", "Risk"],
		"target_types": ["Control"],
		"edge_color": "#c0392b",
	},
}


class ComplianceGraphRelationship(Document):
	"""Controller for Compliance Graph Relationship DocType."""

	def before_insert(self):
		"""Set timestamps before insert."""
		self.created_at = now_datetime()
		self.created_by = frappe.session.user
		if not self.valid_from:
			self.valid_from = now_datetime()

	def validate(self):
		"""Validate relationship constraints."""
		self.validate_no_self_reference()
		self.validate_entity_types()
		self.validate_no_duplicate()

	def validate_no_self_reference(self):
		"""Ensure source and target are different."""
		if self.source_entity == self.target_entity:
			frappe.throw(_("Source and target entities cannot be the same"))

	def validate_entity_types(self):
		"""Validate that entity types match relationship definition."""
		definition = RELATIONSHIP_DEFINITIONS.get(self.relationship_type)
		if not definition:
			return  # Unknown relationship type, skip validation

		# Get entity types
		source_type = frappe.db.get_value("Compliance Graph Entity", self.source_entity, "entity_type")
		target_type = frappe.db.get_value("Compliance Graph Entity", self.target_entity, "entity_type")

		if source_type and definition.get("source_types"):
			if source_type not in definition["source_types"]:
				frappe.throw(
					_("Relationship {0} requires source entity type to be one of: {1}").format(
						self.relationship_type, ", ".join(definition["source_types"])
					)
				)

		if target_type and definition.get("target_types"):
			if target_type not in definition["target_types"]:
				frappe.throw(
					_("Relationship {0} requires target entity type to be one of: {1}").format(
						self.relationship_type, ", ".join(definition["target_types"])
					)
				)

	def validate_no_duplicate(self):
		"""Ensure no duplicate active relationship exists."""
		if self.is_new():
			existing = frappe.db.exists(
				"Compliance Graph Relationship",
				{
					"relationship_type": self.relationship_type,
					"source_entity": self.source_entity,
					"target_entity": self.target_entity,
					"is_active": 1,
				},
			)
			if existing:
				frappe.throw(
					_("An active relationship of type {0} already exists between these entities").format(
						self.relationship_type
					)
				)

	def get_properties_dict(self):
		"""Parse properties JSON and return as dict."""
		if not self.properties:
			return {}

		try:
			return json.loads(self.properties)
		except (json.JSONDecodeError, TypeError):
			return {}

	def set_property(self, key, value):
		"""Set a property in the properties JSON."""
		props = self.get_properties_dict()
		props[key] = value
		self.properties = json.dumps(props, indent=2)

	@staticmethod
	def create_relationship(relationship_type, source_entity, target_entity, weight=1.0, properties=None):
		"""
		Create a new relationship between entities.

		Args:
		    relationship_type: Type of relationship
		    source_entity: Source entity name
		    target_entity: Target entity name
		    weight: Relationship weight (default 1.0)
		    properties: Optional properties dict

		Returns:
		    Compliance Graph Relationship document
		"""
		rel = frappe.get_doc(
			{
				"doctype": "Compliance Graph Relationship",
				"relationship_type": relationship_type,
				"source_entity": source_entity,
				"target_entity": target_entity,
				"weight": weight,
				"is_active": 1,
				"properties": json.dumps(properties) if properties else None,
			}
		)
		rel.insert(ignore_permissions=True)
		return rel

	@staticmethod
	def get_relationships(entity_name, relationship_type=None, direction="both"):
		"""
		Get relationships for an entity.

		Args:
		    entity_name: Entity name to query
		    relationship_type: Optional filter by type
		    direction: "outgoing", "incoming", or "both"

		Returns:
		    List of relationship documents
		"""
		filters = {"is_active": 1}

		if relationship_type:
			filters["relationship_type"] = relationship_type

		if direction == "outgoing":
			filters["source_entity"] = entity_name
		elif direction == "incoming":
			filters["target_entity"] = entity_name
		else:
			# Both directions - need OR condition
			return frappe.get_all(
				"Compliance Graph Relationship",
				filters=filters,
				or_filters=[{"source_entity": entity_name}, {"target_entity": entity_name}],
				fields=[
					"name",
					"relationship_type",
					"source_entity",
					"target_entity",
					"weight",
					"source_entity_type",
					"target_entity_type",
				],
			)

		return frappe.get_all(
			"Compliance Graph Relationship",
			filters=filters,
			fields=[
				"name",
				"relationship_type",
				"source_entity",
				"target_entity",
				"weight",
				"source_entity_type",
				"target_entity_type",
			],
		)

	@staticmethod
	def deactivate_relationships(entity_name):
		"""
		Deactivate all relationships for an entity.

		Args:
		    entity_name: Entity name whose relationships to deactivate
		"""
		# Deactivate outgoing relationships
		frappe.db.sql(
			"""
            UPDATE `tabCompliance Graph Relationship`
            SET is_active = 0, valid_to = %(now)s
            WHERE (source_entity = %(entity)s OR target_entity = %(entity)s)
            AND is_active = 1
        """,
			{"entity": entity_name, "now": now_datetime()},
		)

	def to_vis_edge(self):
		"""
		Convert relationship to vis.js edge format.

		Returns:
		    Dict suitable for vis.js network
		"""
		definition = RELATIONSHIP_DEFINITIONS.get(self.relationship_type, {})

		return {
			"id": self.name,
			"from": self.source_entity,
			"to": self.target_entity,
			"label": self.relationship_type,
			"arrows": "to",
			"color": definition.get("edge_color", "#7f8c8d"),
			"width": max(1, int(self.weight * 3)) if self.weight else 2,
			"title": definition.get("description", self.relationship_type),
			"relationship_type": self.relationship_type,
		}
