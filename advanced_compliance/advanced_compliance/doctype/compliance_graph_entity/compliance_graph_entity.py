"""
Compliance Graph Entity DocType Controller.

Represents a node in the compliance knowledge graph.
Maps to source DocTypes like Control Activity, Risk Register Entry, etc.
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

# Entity type to color mapping for visualization
ENTITY_COLORS = {
	"Control": "#3498db",  # Blue
	"Risk": "#e74c3c",  # Red
	"Person": "#9b59b6",  # Purple
	"Process": "#2ecc71",  # Green
	"Evidence": "#f39c12",  # Orange
	"Requirement": "#1abc9c",  # Teal
	"Objective": "#34495e",  # Dark Gray
	"System": "#95a5a6",  # Light Gray
	"Department": "#e67e22",  # Dark Orange
	"Company": "#27ae60",  # Dark Green
	"Document": "#8e44ad",  # Dark Purple
	"Period": "#16a085",  # Dark Teal
}

# Entity type to size mapping
ENTITY_SIZES = {
	"Control": 30,
	"Risk": 35,
	"Person": 20,
	"Process": 25,
	"Evidence": 20,
	"Requirement": 25,
	"Objective": 25,
	"System": 25,
	"Department": 25,
	"Company": 40,
	"Document": 20,
	"Period": 20,
}


class ComplianceGraphEntity(Document):
	"""Controller for Compliance Graph Entity DocType."""

	def before_insert(self):
		"""Set timestamps and derive label before insert."""
		self.created_at = now_datetime()
		self.modified_at = now_datetime()
		self.set_entity_label()
		self.set_visualization_defaults()

	def before_save(self):
		"""Update modified timestamp and label."""
		self.modified_at = now_datetime()
		self.set_entity_label()

	def set_entity_label(self):
		"""Derive display label from source document if not already set."""
		# Don't overwrite if label already provided
		if self.entity_label:
			return

		if not self.entity_doctype or not self.entity_id:
			return

		try:
			# Get title field for the DocType
			meta = frappe.get_meta(self.entity_doctype)
			title_field = meta.get_title_field()

			if title_field and title_field != "name":
				label = frappe.db.get_value(self.entity_doctype, self.entity_id, title_field)
				self.entity_label = label or self.entity_id
			else:
				self.entity_label = self.entity_id
		except Exception:
			self.entity_label = self.entity_id

	def set_visualization_defaults(self):
		"""Set default color and size based on entity type."""
		if not self.node_color:
			self.node_color = ENTITY_COLORS.get(self.entity_type, "#95a5a6")

		if not self.node_size:
			self.node_size = ENTITY_SIZES.get(self.entity_type, 25)

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

	def get_property(self, key, default=None):
		"""Get a property from the properties JSON."""
		props = self.get_properties_dict()
		return props.get(key, default)

	@staticmethod
	def get_or_create(entity_type, entity_doctype, entity_id):
		"""
		Get existing entity or create new one.

		Args:
		    entity_type: Type of entity (Control, Risk, etc.)
		    entity_doctype: Source DocType name
		    entity_id: Source document name

		Returns:
		    Compliance Graph Entity document
		"""
		existing = frappe.db.get_value(
			"Compliance Graph Entity",
			{"entity_doctype": entity_doctype, "entity_id": entity_id, "is_active": 1},
			"name",
		)

		if existing:
			return frappe.get_doc("Compliance Graph Entity", existing)

		# Create new entity
		entity = frappe.get_doc(
			{
				"doctype": "Compliance Graph Entity",
				"entity_type": entity_type,
				"entity_doctype": entity_doctype,
				"entity_id": entity_id,
				"is_active": 1,
			}
		)
		entity.insert(ignore_permissions=True)
		return entity

	@staticmethod
	def deactivate_for_document(entity_doctype, entity_id):
		"""
		Deactivate entity when source document is deleted.

		Args:
		    entity_doctype: Source DocType name
		    entity_id: Source document name
		"""
		entities = frappe.get_all(
			"Compliance Graph Entity",
			filters={"entity_doctype": entity_doctype, "entity_id": entity_id, "is_active": 1},
			pluck="name",
		)

		for entity_name in entities:
			frappe.db.set_value(
				"Compliance Graph Entity", entity_name, {"is_active": 0, "modified_at": now_datetime()}
			)

	@staticmethod
	def get_by_type(entity_type, active_only=True):
		"""
		Get all entities of a specific type.

		Args:
		    entity_type: Type of entity
		    active_only: Only return active entities

		Returns:
		    List of entity documents
		"""
		filters = {"entity_type": entity_type}
		if active_only:
			filters["is_active"] = 1

		return frappe.get_all(
			"Compliance Graph Entity",
			filters=filters,
			fields=[
				"name",
				"entity_label",
				"entity_doctype",
				"entity_id",
				"node_color",
				"node_size",
				"properties",
			],
		)

	def to_vis_node(self):
		"""
		Convert entity to vis.js node format.

		Returns:
		    Dict suitable for vis.js network
		"""
		return {
			"id": self.name,
			"label": self.entity_label or self.entity_id,
			"title": f"{self.entity_type}: {self.entity_label}",
			"group": self.entity_type,
			"color": self.node_color or ENTITY_COLORS.get(self.entity_type),
			"size": self.node_size or ENTITY_SIZES.get(self.entity_type),
			"entity_type": self.entity_type,
			"entity_doctype": self.entity_doctype,
			"entity_id": self.entity_id,
		}
