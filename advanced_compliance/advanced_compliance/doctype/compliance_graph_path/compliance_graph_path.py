"""
Compliance Graph Path DocType Controller.

Stores pre-computed paths between entities for fast traversal queries.
Paths are recomputed when the graph changes.
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

# Common path types for pre-computation
PATH_TYPES = {
	"RISK_TO_CONTROL": {
		"description": "Path from Risk to mitigating Controls",
		"start_type": "Risk",
		"end_type": "Control",
		"relationship_types": ["MITIGATES"],
	},
	"CONTROL_TO_EVIDENCE": {
		"description": "Path from Control to testing Evidence",
		"start_type": "Control",
		"end_type": "Evidence",
		"relationship_types": ["TESTS"],
	},
	"REQUIREMENT_TO_CONTROL": {
		"description": "Path from Requirement to implementing Controls",
		"start_type": "Requirement",
		"end_type": "Control",
		"relationship_types": ["MANDATES", "ADDRESSES"],
	},
	"PERSON_TO_CONTROL": {
		"description": "Path from Person to owned/performed Controls",
		"start_type": "Person",
		"end_type": "Control",
		"relationship_types": ["OWNS", "PERFORMS"],
	},
	"CONTROL_TO_PROCESS": {
		"description": "Path from Control to supported Processes",
		"start_type": "Control",
		"end_type": "Process",
		"relationship_types": ["SUPPORTS"],
	},
	"CONTROL_DEPENDENCY": {
		"description": "Path showing Control dependencies",
		"start_type": "Control",
		"end_type": "Control",
		"relationship_types": ["DEPENDS_ON", "PRECEDED_BY"],
	},
}


class ComplianceGraphPath(Document):
	"""Controller for Compliance Graph Path DocType."""

	def before_insert(self):
		"""Set computed timestamp before insert."""
		self.computed_at = now_datetime()
		self.compute_path_length()

	def compute_path_length(self):
		"""Compute path length from entities list."""
		if self.path_entities:
			try:
				entities = json.loads(self.path_entities)
				self.path_length = len(entities) - 1 if entities else 0
			except (json.JSONDecodeError, TypeError):
				self.path_length = 0
		else:
			self.path_length = 0

	def get_path_entities_list(self):
		"""Get path entities as a list."""
		if not self.path_entities:
			return []
		try:
			return json.loads(self.path_entities)
		except (json.JSONDecodeError, TypeError):
			return []

	def get_path_relationships_list(self):
		"""Get path relationships as a list."""
		if not self.path_relationships:
			return []
		try:
			return json.loads(self.path_relationships)
		except (json.JSONDecodeError, TypeError):
			return []

	@staticmethod
	def create_path(path_type, start_entity, end_entity, entities, relationships):
		"""
		Create a new computed path.

		Args:
		    path_type: Type of path
		    start_entity: Start entity name
		    end_entity: End entity name
		    entities: List of entity names in path
		    relationships: List of relationship names in path

		Returns:
		    Compliance Graph Path document
		"""
		path = frappe.get_doc(
			{
				"doctype": "Compliance Graph Path",
				"path_type": path_type,
				"start_entity": start_entity,
				"end_entity": end_entity,
				"path_entities": json.dumps(entities),
				"path_relationships": json.dumps(relationships),
				"is_valid": 1,
			}
		)
		path.insert(ignore_permissions=True)
		return path

	@staticmethod
	def invalidate_paths(entity_name=None, path_type=None):
		"""
		Invalidate computed paths.

		Args:
		    entity_name: Invalidate paths containing this entity
		    path_type: Invalidate paths of this type
		"""
		filters = {"is_valid": 1}

		if path_type:
			filters["path_type"] = path_type

		if entity_name:
			# Need to find paths containing this entity
			paths = frappe.get_all("Compliance Graph Path", filters=filters, fields=["name", "path_entities"])

			for path in paths:
				try:
					entities = json.loads(path.path_entities or "[]")
					if entity_name in entities:
						frappe.db.set_value("Compliance Graph Path", path.name, "is_valid", 0)
				except (json.JSONDecodeError, TypeError):
					continue
		else:
			# Invalidate all matching paths
			frappe.db.set_value("Compliance Graph Path", filters, "is_valid", 0)

	@staticmethod
	def get_paths(start_entity=None, end_entity=None, path_type=None):
		"""
		Get computed paths matching criteria.

		Args:
		    start_entity: Filter by start entity
		    end_entity: Filter by end entity
		    path_type: Filter by path type

		Returns:
		    List of path documents
		"""
		filters = {"is_valid": 1}

		if start_entity:
			filters["start_entity"] = start_entity
		if end_entity:
			filters["end_entity"] = end_entity
		if path_type:
			filters["path_type"] = path_type

		return frappe.get_all(
			"Compliance Graph Path",
			filters=filters,
			fields=[
				"name",
				"path_type",
				"start_entity",
				"end_entity",
				"path_length",
				"path_entities",
				"path_relationships",
				"computed_at",
			],
		)

	@staticmethod
	def cleanup_invalid_paths():
		"""Remove all invalid paths."""
		frappe.db.delete("Compliance Graph Path", {"is_valid": 0})

	def to_path_data(self):
		"""
		Convert to path visualization data.

		Returns:
		    Dict with path details for visualization
		"""
		return {
			"path_type": self.path_type,
			"start": self.start_entity,
			"end": self.end_entity,
			"length": self.path_length,
			"entities": self.get_path_entities_list(),
			"relationships": self.get_path_relationships_list(),
			"computed_at": str(self.computed_at) if self.computed_at else None,
		}
