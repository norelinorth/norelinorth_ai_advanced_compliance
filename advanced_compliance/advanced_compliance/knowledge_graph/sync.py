"""
Graph Sync Engine.

Automatically synchronizes Frappe DocTypes with the knowledge graph.
Creates and updates graph entities and relationships based on document changes.
"""

import json

import frappe
from frappe import _
from frappe.utils import now_datetime

# Mapping from DocType to entity type
DOCTYPE_TO_ENTITY_TYPE = {
	"Control Activity": "Control",
	"Risk Register Entry": "Risk",
	"User": "Person",
	"Control Evidence": "Evidence",
	"Test Execution": "Evidence",
	"Department": "Department",
	"Company": "Company",
}

# Fields that define relationships between DocTypes
RELATIONSHIP_FIELDS = {
	"Control Activity": {
		"control_owner": {
			"relationship_type": "OWNS",
			"target_doctype": "User",
			"target_entity_type": "Person",
			"direction": "incoming",  # Person OWNS Control
		},
		"control_performer": {
			"relationship_type": "PERFORMS",
			"target_doctype": "User",
			"target_entity_type": "Person",
			"direction": "incoming",
		},
		"risks_addressed": {
			"relationship_type": "MITIGATES",
			"target_doctype": "Risk Register Entry",
			"target_entity_type": "Risk",
			"direction": "outgoing",  # Control MITIGATES Risk
			"is_child_table": True,
			"link_field": "risk",
		},
		"company": {
			"relationship_type": "BELONGS_TO",
			"target_doctype": "Company",
			"target_entity_type": "Company",
			"direction": "outgoing",
		},
		"department": {
			"relationship_type": "BELONGS_TO",
			"target_doctype": "Department",
			"target_entity_type": "Department",
			"direction": "outgoing",
		},
	},
	"Risk Register Entry": {
		"risk_owner": {
			"relationship_type": "OWNS",
			"target_doctype": "User",
			"target_entity_type": "Person",
			"direction": "incoming",  # Person OWNS Risk
		},
		"company": {
			"relationship_type": "BELONGS_TO",
			"target_doctype": "Company",
			"target_entity_type": "Company",
			"direction": "outgoing",
		},
		"department": {
			"relationship_type": "BELONGS_TO",
			"target_doctype": "Department",
			"target_entity_type": "Department",
			"direction": "outgoing",
		},
	},
	"Control Evidence": {
		"control_activity": {
			"relationship_type": "TESTS",
			"target_doctype": "Control Activity",
			"target_entity_type": "Control",
			"direction": "outgoing",  # Evidence TESTS Control
		}
	},
	"Test Execution": {
		"control": {
			"relationship_type": "TESTS",
			"target_doctype": "Control Activity",
			"target_entity_type": "Control",
			"direction": "outgoing",
		},
		"tester": {
			"relationship_type": "EXECUTES",
			"target_doctype": "User",
			"target_entity_type": "Person",
			"direction": "incoming",  # Person EXECUTES this test
		},
	},
}


class GraphSyncEngine:
	"""Engine for synchronizing DocTypes with the knowledge graph."""

	def __init__(self):
		"""Initialize the sync engine."""
		self.entity_cache = {}

	def sync_document(self, doc, event_type="update"):
		"""
		Sync a document to the knowledge graph.

		Args:
		    doc: The Frappe document
		    event_type: "create", "update", or "delete"
		"""
		doctype = doc.doctype
		entity_type = DOCTYPE_TO_ENTITY_TYPE.get(doctype)

		if not entity_type:
			return  # DocType not mapped

		if event_type == "delete":
			self._handle_delete(doc, entity_type)
		else:
			self._sync_entity(doc, entity_type)
			self._sync_relationships(doc)

	def _sync_entity(self, doc, entity_type):
		"""Create or update entity for document."""
		from advanced_compliance.advanced_compliance.doctype.compliance_graph_entity.compliance_graph_entity import (
			ComplianceGraphEntity,
		)

		entity = ComplianceGraphEntity.get_or_create(
			entity_type=entity_type, entity_doctype=doc.doctype, entity_id=doc.name
		)

		# Update properties
		properties = self._extract_properties(doc)
		if properties:
			entity.properties = json.dumps(properties)
			entity.save(ignore_permissions=True)

		self.entity_cache[f"{doc.doctype}:{doc.name}"] = entity.name
		return entity

	def _extract_properties(self, doc):
		"""Extract relevant properties from document for graph storage."""
		properties = {}

		# Common fields to extract
		common_fields = ["status", "company", "department"]
		for field in common_fields:
			if hasattr(doc, field) and doc.get(field):
				properties[field] = doc.get(field)

		# DocType-specific fields
		if doc.doctype == "Control Activity":
			for field in ["control_type", "automation_level", "frequency", "is_key_control"]:
				if hasattr(doc, field) and doc.get(field):
					properties[field] = doc.get(field)

		elif doc.doctype == "Risk Register Entry":
			for field in ["risk_category", "likelihood", "impact", "inherent_risk_score"]:
				if hasattr(doc, field) and doc.get(field):
					properties[field] = doc.get(field)

		return properties

	def _sync_relationships(self, doc):
		"""Sync relationships for document."""
		rel_config = RELATIONSHIP_FIELDS.get(doc.doctype, {})

		for field_name, config in rel_config.items():
			if config.get("is_child_table"):
				self._sync_child_table_relationships(doc, field_name, config)
			else:
				self._sync_field_relationship(doc, field_name, config)

	def _sync_field_relationship(self, doc, field_name, config):
		"""Sync relationship from a link field."""
		target_value = doc.get(field_name)
		if not target_value:
			return

		# Get or create source entity
		source_entity = self._get_entity_for_doc(doc)
		if not source_entity:
			return

		# Get or create target entity
		target_entity = self._get_or_create_entity(
			config["target_entity_type"], config["target_doctype"], target_value
		)
		if not target_entity:
			return

		# Determine source and target based on direction
		if config["direction"] == "incoming":
			rel_source = target_entity
			rel_target = source_entity
		else:
			rel_source = source_entity
			rel_target = target_entity

		# Create relationship if it doesn't exist
		self._create_relationship_if_not_exists(config["relationship_type"], rel_source, rel_target)

	def _sync_child_table_relationships(self, doc, field_name, config):
		"""Sync relationships from a child table."""
		child_table = doc.get(field_name) or []
		link_field = config.get("link_field", "name")

		source_entity = self._get_entity_for_doc(doc)
		if not source_entity:
			return

		for row in child_table:
			target_value = row.get(link_field)
			if not target_value:
				continue

			target_entity = self._get_or_create_entity(
				config["target_entity_type"], config["target_doctype"], target_value
			)
			if not target_entity:
				continue

			if config["direction"] == "incoming":
				rel_source = target_entity
				rel_target = source_entity
			else:
				rel_source = source_entity
				rel_target = target_entity

			self._create_relationship_if_not_exists(config["relationship_type"], rel_source, rel_target)

	def _get_entity_for_doc(self, doc):
		"""Get entity name for a document."""
		cache_key = f"{doc.doctype}:{doc.name}"
		if cache_key in self.entity_cache:
			return self.entity_cache[cache_key]

		entity_type = DOCTYPE_TO_ENTITY_TYPE.get(doc.doctype)
		if not entity_type:
			return None

		entity_name = frappe.db.get_value(
			"Compliance Graph Entity",
			{"entity_doctype": doc.doctype, "entity_id": doc.name, "is_active": 1},
			"name",
		)

		if entity_name:
			self.entity_cache[cache_key] = entity_name

		return entity_name

	def _get_or_create_entity(self, entity_type, doctype, doc_name):
		"""Get or create an entity for a document reference."""
		cache_key = f"{doctype}:{doc_name}"
		if cache_key in self.entity_cache:
			return self.entity_cache[cache_key]

		# Check if document exists
		if not frappe.db.exists(doctype, doc_name):
			return None

		from advanced_compliance.advanced_compliance.doctype.compliance_graph_entity.compliance_graph_entity import (
			ComplianceGraphEntity,
		)

		entity = ComplianceGraphEntity.get_or_create(
			entity_type=entity_type, entity_doctype=doctype, entity_id=doc_name
		)

		self.entity_cache[cache_key] = entity.name
		return entity.name

	def _create_relationship_if_not_exists(self, relationship_type, source_entity, target_entity):
		"""Create relationship if it doesn't already exist."""
		existing = frappe.db.exists(
			"Compliance Graph Relationship",
			{
				"relationship_type": relationship_type,
				"source_entity": source_entity,
				"target_entity": target_entity,
				"is_active": 1,
			},
		)

		if not existing:
			from advanced_compliance.advanced_compliance.doctype.compliance_graph_relationship.compliance_graph_relationship import (
				ComplianceGraphRelationship,
			)

			ComplianceGraphRelationship.create_relationship(
				relationship_type=relationship_type, source_entity=source_entity, target_entity=target_entity
			)

	def _handle_delete(self, doc, entity_type):
		"""Handle document deletion."""
		from advanced_compliance.advanced_compliance.doctype.compliance_graph_entity.compliance_graph_entity import (
			ComplianceGraphEntity,
		)
		from advanced_compliance.advanced_compliance.doctype.compliance_graph_path.compliance_graph_path import (
			ComplianceGraphPath,
		)
		from advanced_compliance.advanced_compliance.doctype.compliance_graph_relationship.compliance_graph_relationship import (
			ComplianceGraphRelationship,
		)

		# Get entity
		entity_name = frappe.db.get_value(
			"Compliance Graph Entity",
			{"entity_doctype": doc.doctype, "entity_id": doc.name, "is_active": 1},
			"name",
		)

		if entity_name:
			# Deactivate relationships
			ComplianceGraphRelationship.deactivate_relationships(entity_name)

			# Invalidate paths
			ComplianceGraphPath.invalidate_paths(entity_name=entity_name)

			# Deactivate entity
			ComplianceGraphEntity.deactivate_for_document(doc.doctype, doc.name)


# Document event handlers
def on_control_created(doc, method):
	"""Handle Control Activity creation."""
	sync = GraphSyncEngine()
	sync.sync_document(doc, "create")


def on_control_updated(doc, method):
	"""Handle Control Activity update."""
	sync = GraphSyncEngine()
	sync.sync_document(doc, "update")


def on_control_deleted(doc, method):
	"""Handle Control Activity deletion."""
	sync = GraphSyncEngine()
	sync.sync_document(doc, "delete")


def on_risk_created(doc, method):
	"""Handle Risk Register Entry creation."""
	sync = GraphSyncEngine()
	sync.sync_document(doc, "create")


def on_risk_updated(doc, method):
	"""Handle Risk Register Entry update."""
	sync = GraphSyncEngine()
	sync.sync_document(doc, "update")


def on_evidence_created(doc, method):
	"""Handle Control Evidence creation."""
	sync = GraphSyncEngine()
	sync.sync_document(doc, "create")


def on_test_created(doc, method):
	"""Handle Test Execution creation."""
	sync = GraphSyncEngine()
	sync.sync_document(doc, "create")


def on_test_updated(doc, method):
	"""Handle Test Execution update."""
	sync = GraphSyncEngine()
	sync.sync_document(doc, "update")


@frappe.whitelist()
def rebuild_graph():
	"""
	Rebuild entire knowledge graph from scratch.

	API endpoint for manual graph rebuild.
	Uses savepoint for transaction safety - if rebuild fails, data is preserved.
	"""
	if not frappe.has_permission("Compliance Graph Entity", "create"):
		frappe.throw(_("No permission to rebuild graph"))

	try:
		# Create savepoint for rollback on failure
		frappe.db.savepoint("rebuild_graph_start")

		# Clear existing graph data
		frappe.db.delete("Compliance Graph Path")
		frappe.db.delete("Compliance Graph Relationship")
		frappe.db.delete("Compliance Graph Entity")

		sync = GraphSyncEngine()
		stats = {"entities": 0, "relationships": 0}

		# Sync Companies first (as they are referenced by other entities)
		companies = frappe.get_all("Company", pluck="name")
		for company_name in companies:
			from advanced_compliance.advanced_compliance.doctype.compliance_graph_entity.compliance_graph_entity import (
				ComplianceGraphEntity,
			)

			ComplianceGraphEntity.get_or_create(
				entity_type="Company", entity_doctype="Company", entity_id=company_name
			)
			stats["entities"] += 1

		# Sync Departments
		departments = frappe.get_all("Department", pluck="name")
		for dept_name in departments:
			from advanced_compliance.advanced_compliance.doctype.compliance_graph_entity.compliance_graph_entity import (
				ComplianceGraphEntity,
			)

			ComplianceGraphEntity.get_or_create(
				entity_type="Department", entity_doctype="Department", entity_id=dept_name
			)
			stats["entities"] += 1

		# Sync all Control Activities
		controls = frappe.get_all("Control Activity", pluck="name")
		for control_name in controls:
			doc = frappe.get_doc("Control Activity", control_name)
			sync.sync_document(doc, "create")
			stats["entities"] += 1

		# Sync all Risk Register Entries
		risks = frappe.get_all("Risk Register Entry", pluck="name")
		for risk_name in risks:
			doc = frappe.get_doc("Risk Register Entry", risk_name)
			sync.sync_document(doc, "create")
			stats["entities"] += 1

		# Sync all Control Evidence
		evidence = frappe.get_all("Control Evidence", pluck="name")
		for evidence_name in evidence:
			doc = frappe.get_doc("Control Evidence", evidence_name)
			sync.sync_document(doc, "create")
			stats["entities"] += 1

		# Sync all Test Executions
		tests = frappe.get_all("Test Execution", pluck="name")
		for test_name in tests:
			doc = frappe.get_doc("Test Execution", test_name)
			sync.sync_document(doc, "create")
			stats["entities"] += 1

		# Count relationships
		stats["relationships"] = frappe.db.count("Compliance Graph Relationship")

		# Release savepoint on success
		frappe.db.release_savepoint("rebuild_graph_start")

		frappe.msgprint(
			_("Graph rebuilt: {0} entities, {1} relationships").format(
				stats["entities"], stats["relationships"]
			)
		)

		return stats

	except Exception as e:
		# Rollback to savepoint on failure - preserves original data
		frappe.db.rollback(save_point="rebuild_graph_start")
		frappe.log_error(message=frappe.get_traceback(), title=_("Graph Rebuild Failed"))
		frappe.throw(_("Graph rebuild failed. Original data preserved. Error: {0}").format(str(e)))
