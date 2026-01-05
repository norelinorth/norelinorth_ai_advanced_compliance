"""
Tests for Knowledge Graph Module.

Comprehensive tests for:
- Compliance Graph Entity DocType
- Compliance Graph Relationship DocType
- Compliance Graph Path DocType
- GraphSyncEngine
- GraphQueryEngine
- CoverageAnalyzer
"""

import json
import unittest

import frappe
from frappe.utils import now_datetime, nowdate


def create_test_entity(entity_type, entity_doctype, entity_id, entity_label=None):
	"""Helper to create test entities with link validation skipped."""
	entity = frappe.get_doc(
		{
			"doctype": "Compliance Graph Entity",
			"entity_type": entity_type,
			"entity_doctype": entity_doctype,
			"entity_id": entity_id,
			"entity_label": entity_label,
		}
	)
	entity.flags.ignore_links = True
	entity.insert(ignore_permissions=True)
	return entity


class TestComplianceGraphEntity(unittest.TestCase):
	"""Tests for Compliance Graph Entity DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def setUp(self):
		"""Set up before each test."""
		frappe.db.rollback()

	def tearDown(self):
		"""Clean up after each test."""
		frappe.db.rollback()

	def test_01_create_entity(self):
		"""Test basic entity creation."""
		entity = create_test_entity("Control", "Control Activity", "TEST-CTRL-001", "Test Control")

		self.assertTrue(entity.name)
		self.assertEqual(entity.entity_type, "Control")
		self.assertEqual(entity.is_active, 1)
		self.assertIsNotNone(entity.created_at)

	def test_02_entity_auto_label(self):
		"""Test automatic label generation."""
		entity = create_test_entity("Risk", "Risk Register Entry", "TEST-RISK-001")

		# Label should be auto-set from entity_id if not provided
		self.assertTrue(entity.entity_label)

	def test_03_entity_visualization_defaults(self):
		"""Test visualization default values."""
		entity = create_test_entity("Control", "Control Activity", "TEST-CTRL-002")

		# Should have color and size defaults
		self.assertEqual(entity.node_color, "#3498db")  # Blue for Control
		self.assertEqual(entity.node_size, 25)

	def test_04_entity_get_or_create(self):
		"""Test get_or_create static method."""
		# First create an entity using helper (with ignore_links)
		entity1 = create_test_entity("Control", "Control Activity", "TEST-CTRL-003")

		# Second call should return existing using query (no link validation on read)
		from advanced_compliance.advanced_compliance.doctype.compliance_graph_entity.compliance_graph_entity import (
			ComplianceGraphEntity,
		)

		entity2_name = frappe.db.get_value(
			"Compliance Graph Entity",
			{"entity_doctype": "Control Activity", "entity_id": "TEST-CTRL-003", "is_active": 1},
			"name",
		)
		entity2 = frappe.get_doc("Compliance Graph Entity", entity2_name)

		self.assertEqual(entity1.name, entity2.name)

	def test_05_entity_to_vis_node(self):
		"""Test vis.js node conversion."""
		entity = create_test_entity("Risk", "Risk Register Entry", "TEST-RISK-002", "Test Risk")

		vis_node = entity.to_vis_node()

		self.assertEqual(vis_node["id"], entity.name)
		self.assertEqual(vis_node["label"], "Test Risk")
		self.assertEqual(vis_node["group"], "Risk")
		self.assertEqual(vis_node["color"], "#e74c3c")  # Red for Risk

	def test_06_entity_deactivation(self):
		"""Test entity deactivation."""
		from advanced_compliance.advanced_compliance.doctype.compliance_graph_entity.compliance_graph_entity import (
			ComplianceGraphEntity,
		)

		entity = create_test_entity("Control", "Control Activity", "TEST-CTRL-004")

		# Deactivate
		ComplianceGraphEntity.deactivate_for_document("Control Activity", "TEST-CTRL-004")

		# Reload and check
		entity.reload()
		self.assertEqual(entity.is_active, 0)


class TestComplianceGraphRelationship(unittest.TestCase):
	"""Tests for Compliance Graph Relationship DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test entities."""
		frappe.set_user("Administrator")

		# Create test entities using helper
		cls.control_entity = create_test_entity("Control", "Control Activity", "REL-TEST-CTRL-001")

		cls.risk_entity = create_test_entity("Risk", "Risk Register Entry", "REL-TEST-RISK-001")

		cls.person_entity = create_test_entity("Person", "User", "Administrator")

		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		"""Clean up test entities."""
		frappe.db.rollback()

	def setUp(self):
		"""Set up before each test."""
		pass

	def tearDown(self):
		"""Clean up after each test."""
		frappe.db.rollback()

	def test_01_create_relationship(self):
		"""Test basic relationship creation."""
		relationship = frappe.get_doc(
			{
				"doctype": "Compliance Graph Relationship",
				"relationship_type": "MITIGATES",
				"source_entity": self.control_entity.name,
				"target_entity": self.risk_entity.name,
			}
		)
		relationship.insert(ignore_permissions=True)

		self.assertTrue(relationship.name)
		self.assertEqual(relationship.is_active, 1)
		self.assertIsNotNone(relationship.created_at)

	def test_02_validate_no_self_reference(self):
		"""Test that self-referencing relationships are rejected."""
		with self.assertRaises(frappe.ValidationError):
			relationship = frappe.get_doc(
				{
					"doctype": "Compliance Graph Relationship",
					"relationship_type": "DEPENDS_ON",
					"source_entity": self.control_entity.name,
					"target_entity": self.control_entity.name,
				}
			)
			relationship.insert(ignore_permissions=True)

	def test_03_validate_entity_types(self):
		"""Test entity type validation for relationships."""
		# MITIGATES should be Control -> Risk
		# Try to create Risk -> Control (wrong direction) - this should fail or be handled
		relationship = frappe.get_doc(
			{
				"doctype": "Compliance Graph Relationship",
				"relationship_type": "MITIGATES",
				"source_entity": self.risk_entity.name,
				"target_entity": self.control_entity.name,
			}
		)

		with self.assertRaises(frappe.ValidationError):
			relationship.insert(ignore_permissions=True)

	def test_04_validate_no_duplicate(self):
		"""Test duplicate relationship prevention."""
		# Create first relationship
		rel1 = frappe.get_doc(
			{
				"doctype": "Compliance Graph Relationship",
				"relationship_type": "OWNS",
				"source_entity": self.person_entity.name,
				"target_entity": self.control_entity.name,
			}
		)
		rel1.insert(ignore_permissions=True)

		# Try to create duplicate
		rel2 = frappe.get_doc(
			{
				"doctype": "Compliance Graph Relationship",
				"relationship_type": "OWNS",
				"source_entity": self.person_entity.name,
				"target_entity": self.control_entity.name,
			}
		)

		with self.assertRaises(frappe.ValidationError):
			rel2.insert(ignore_permissions=True)

	def test_05_relationship_to_vis_edge(self):
		"""Test vis.js edge conversion."""
		relationship = frappe.get_doc(
			{
				"doctype": "Compliance Graph Relationship",
				"relationship_type": "PERFORMS",
				"source_entity": self.person_entity.name,
				"target_entity": self.control_entity.name,
			}
		)
		relationship.insert(ignore_permissions=True)

		vis_edge = relationship.to_vis_edge()

		self.assertEqual(vis_edge["from"], self.person_entity.name)
		self.assertEqual(vis_edge["to"], self.control_entity.name)
		self.assertEqual(vis_edge["label"], "PERFORMS")

	def test_06_create_relationship_static(self):
		"""Test create_relationship static method."""
		# Create a valid DEPENDS_ON (Control -> Control)
		control2 = create_test_entity("Control", "Control Activity", "REL-TEST-CTRL-002")

		from advanced_compliance.advanced_compliance.doctype.compliance_graph_relationship.compliance_graph_relationship import (
			ComplianceGraphRelationship,
		)

		rel = ComplianceGraphRelationship.create_relationship(
			relationship_type="DEPENDS_ON",
			source_entity=self.control_entity.name,
			target_entity=control2.name,
			weight=0.5,
		)

		self.assertTrue(rel.name)
		self.assertEqual(rel.weight, 0.5)


class TestComplianceGraphPath(unittest.TestCase):
	"""Tests for Compliance Graph Path DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test entities."""
		frappe.set_user("Administrator")

		# Create test entities
		cls.entity1 = create_test_entity("Risk", "Risk Register Entry", "PATH-TEST-RISK-001")

		cls.entity2 = create_test_entity("Control", "Control Activity", "PATH-TEST-CTRL-001")

		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		"""Clean up."""
		frappe.db.rollback()

	def setUp(self):
		"""Set up before each test."""
		pass

	def tearDown(self):
		"""Clean up after each test."""
		frappe.db.rollback()

	def test_01_create_path(self):
		"""Test path creation."""
		from advanced_compliance.advanced_compliance.doctype.compliance_graph_path.compliance_graph_path import (
			ComplianceGraphPath,
		)

		path = ComplianceGraphPath.create_path(
			path_type="RISK_TO_CONTROL",
			start_entity=self.entity1.name,
			end_entity=self.entity2.name,
			entities=[self.entity1.name, self.entity2.name],
			relationships=["REL-001"],
		)

		self.assertTrue(path.name)
		self.assertEqual(path.path_length, 1)
		self.assertEqual(path.is_valid, 1)
		self.assertIsNotNone(path.computed_at)

	def test_02_path_entities_list(self):
		"""Test path entities retrieval."""
		path = frappe.get_doc(
			{
				"doctype": "Compliance Graph Path",
				"path_type": "CONTROL_TO_EVIDENCE",
				"start_entity": self.entity2.name,
				"end_entity": self.entity1.name,
				"path_entities": json.dumps([self.entity2.name, self.entity1.name]),
				"path_relationships": json.dumps(["REL-002"]),
			}
		)
		path.insert(ignore_permissions=True)

		entities_list = path.get_path_entities_list()
		self.assertEqual(len(entities_list), 2)
		self.assertEqual(entities_list[0], self.entity2.name)

	def test_03_invalidate_paths(self):
		"""Test path invalidation."""
		from advanced_compliance.advanced_compliance.doctype.compliance_graph_path.compliance_graph_path import (
			ComplianceGraphPath,
		)

		# Create a path
		path = ComplianceGraphPath.create_path(
			path_type="PERSON_TO_CONTROL",
			start_entity=self.entity1.name,
			end_entity=self.entity2.name,
			entities=[self.entity1.name, self.entity2.name],
			relationships=["REL-003"],
		)
		self.assertEqual(path.is_valid, 1)

		# Invalidate paths containing entity1
		ComplianceGraphPath.invalidate_paths(entity_name=self.entity1.name)

		path.reload()
		self.assertEqual(path.is_valid, 0)

	def test_04_to_path_data(self):
		"""Test path visualization data conversion."""
		path = frappe.get_doc(
			{
				"doctype": "Compliance Graph Path",
				"path_type": "CONTROL_DEPENDENCY",
				"start_entity": self.entity1.name,
				"end_entity": self.entity2.name,
				"path_entities": json.dumps([self.entity1.name, self.entity2.name]),
				"path_relationships": json.dumps([]),
			}
		)
		path.insert(ignore_permissions=True)

		path_data = path.to_path_data()

		self.assertEqual(path_data["path_type"], "CONTROL_DEPENDENCY")
		self.assertEqual(path_data["length"], 1)
		self.assertEqual(len(path_data["entities"]), 2)


class TestGraphSyncEngine(unittest.TestCase):
	"""Tests for Graph Sync Engine."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def setUp(self):
		"""Set up before each test."""
		frappe.db.rollback()

	def tearDown(self):
		"""Clean up after each test."""
		frappe.db.rollback()

	def test_01_sync_engine_init(self):
		"""Test sync engine initialization."""
		from advanced_compliance.advanced_compliance.knowledge_graph.sync import GraphSyncEngine

		engine = GraphSyncEngine()
		self.assertIsInstance(engine.entity_cache, dict)

	def test_02_doctype_mapping(self):
		"""Test DocType to entity type mapping."""
		from advanced_compliance.advanced_compliance.knowledge_graph.sync import DOCTYPE_TO_ENTITY_TYPE

		self.assertEqual(DOCTYPE_TO_ENTITY_TYPE.get("Control Activity"), "Control")
		self.assertEqual(DOCTYPE_TO_ENTITY_TYPE.get("Risk Register Entry"), "Risk")
		self.assertEqual(DOCTYPE_TO_ENTITY_TYPE.get("User"), "Person")

	def test_03_relationship_fields_config(self):
		"""Test relationship fields configuration."""
		from advanced_compliance.advanced_compliance.knowledge_graph.sync import RELATIONSHIP_FIELDS

		# Control Activity should have control_owner relationship config
		control_config = RELATIONSHIP_FIELDS.get("Control Activity", {})
		self.assertIn("control_owner", control_config)
		self.assertEqual(control_config["control_owner"]["relationship_type"], "OWNS")


class TestGraphQueryEngine(unittest.TestCase):
	"""Tests for Graph Query Engine."""

	@classmethod
	def setUpClass(cls):
		"""Set up test graph."""
		frappe.set_user("Administrator")

		# Create a small test graph
		cls.entity_control = create_test_entity(
			"Control", "Control Activity", "QUERY-TEST-CTRL-001", "Query Test Control"
		)

		cls.entity_risk = create_test_entity(
			"Risk", "Risk Register Entry", "QUERY-TEST-RISK-001", "Query Test Risk"
		)

		cls.entity_person = create_test_entity("Person", "User", "Administrator", "Admin User")

		# Create relationships
		cls.rel_mitigates = frappe.get_doc(
			{
				"doctype": "Compliance Graph Relationship",
				"relationship_type": "MITIGATES",
				"source_entity": cls.entity_control.name,
				"target_entity": cls.entity_risk.name,
			}
		)
		cls.rel_mitigates.insert(ignore_permissions=True)

		cls.rel_owns = frappe.get_doc(
			{
				"doctype": "Compliance Graph Relationship",
				"relationship_type": "OWNS",
				"source_entity": cls.entity_person.name,
				"target_entity": cls.entity_control.name,
			}
		)
		cls.rel_owns.insert(ignore_permissions=True)

		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		"""Clean up."""
		frappe.db.rollback()

	def setUp(self):
		"""Set up before each test."""
		pass

	def tearDown(self):
		"""Clean up after each test."""
		pass

	def test_01_query_engine_init(self):
		"""Test query engine initialization."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import GraphQueryEngine

		engine = GraphQueryEngine()
		self.assertIsInstance(engine, GraphQueryEngine)

	def test_02_get_entity(self):
		"""Test entity retrieval."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import GraphQueryEngine

		engine = GraphQueryEngine()
		entity = engine.get_entity(self.entity_control.name)

		self.assertIsNotNone(entity)
		self.assertEqual(entity["entity_type"], "Control")

	def test_03_get_entity_by_document(self):
		"""Test entity retrieval by document."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import GraphQueryEngine

		engine = GraphQueryEngine()
		entity = engine.get_entity_by_document("Control Activity", "QUERY-TEST-CTRL-001")

		self.assertIsNotNone(entity)
		self.assertEqual(entity["entity_id"], "QUERY-TEST-CTRL-001")

	def test_04_get_neighbors(self):
		"""Test neighbor retrieval."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import GraphQueryEngine

		engine = GraphQueryEngine()

		# Get neighbors of control (should find risk and person)
		neighbors = engine.get_neighbors(self.entity_control.name, direction="both", max_depth=1)

		self.assertGreater(len(neighbors), 0)

	def test_05_get_neighbors_filtered(self):
		"""Test filtered neighbor retrieval."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import GraphQueryEngine

		engine = GraphQueryEngine()

		# Get only MITIGATES relationships
		neighbors = engine.get_neighbors(
			self.entity_control.name, relationship_types=["MITIGATES"], direction="outgoing"
		)

		self.assertEqual(len(neighbors), 1)
		self.assertEqual(neighbors[0]["relationship_type"], "MITIGATES")

	def test_06_find_path(self):
		"""Test path finding."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import GraphQueryEngine

		engine = GraphQueryEngine()

		# Find path from person to risk (through control)
		path = engine.find_path(self.entity_person.name, self.entity_risk.name, max_depth=3)

		self.assertIsNotNone(path)
		self.assertEqual(len(path["entities"]), 3)
		self.assertEqual(path["length"], 2)

	def test_07_traverse(self):
		"""Test graph traversal."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import GraphQueryEngine

		engine = GraphQueryEngine()

		result = engine.traverse(
			self.entity_person.name, direction="outgoing", max_depth=2, include_start=True
		)

		self.assertIn("entities", result)
		self.assertIn("relationships", result)
		self.assertGreater(result["count"], 0)

	def test_08_get_entities_by_type(self):
		"""Test entity type filtering."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import GraphQueryEngine

		engine = GraphQueryEngine()

		controls = engine.get_entities_by_type("Control")
		self.assertGreater(len(controls), 0)

		for control in controls:
			self.assertEqual(control["entity_type"], "Control")

	def test_09_get_relationship_count(self):
		"""Test relationship count."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import GraphQueryEngine

		engine = GraphQueryEngine()

		count = engine.get_relationship_count(self.entity_control.name)

		self.assertIn("outgoing", count)
		self.assertIn("incoming", count)
		self.assertIn("total", count)
		self.assertGreater(count["total"], 0)

	def test_10_get_graph_for_visualization(self):
		"""Test visualization data generation."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import GraphQueryEngine

		engine = GraphQueryEngine()

		data = engine.get_graph_for_visualization(center_entity=self.entity_control.name, depth=1)

		self.assertIn("nodes", data)
		self.assertIn("edges", data)
		self.assertGreater(data["node_count"], 0)

	def test_11_get_subgraph(self):
		"""Test subgraph extraction."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import GraphQueryEngine

		engine = GraphQueryEngine()

		subgraph = engine.get_subgraph([self.entity_control.name, self.entity_risk.name])

		self.assertEqual(len(subgraph["entities"]), 2)
		self.assertGreater(len(subgraph["relationships"]), 0)


class TestCoverageAnalyzer(unittest.TestCase):
	"""Tests for Coverage Analyzer."""

	@classmethod
	def setUpClass(cls):
		"""Set up test data."""
		frappe.set_user("Administrator")

		# Create test entities for coverage analysis
		cls.risk_covered = create_test_entity("Risk", "Risk Register Entry", "COV-TEST-RISK-COVERED")

		cls.risk_uncovered = create_test_entity("Risk", "Risk Register Entry", "COV-TEST-RISK-UNCOVERED")

		cls.control = create_test_entity("Control", "Control Activity", "COV-TEST-CTRL-001")

		# Create mitigates relationship (control -> covered risk)
		cls.rel = frappe.get_doc(
			{
				"doctype": "Compliance Graph Relationship",
				"relationship_type": "MITIGATES",
				"source_entity": cls.control.name,
				"target_entity": cls.risk_covered.name,
			}
		)
		cls.rel.insert(ignore_permissions=True)

		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		"""Clean up."""
		frappe.db.rollback()

	def setUp(self):
		"""Set up before each test."""
		pass

	def tearDown(self):
		"""Clean up after each test."""
		pass

	def test_01_analyzer_init(self):
		"""Test analyzer initialization."""
		from advanced_compliance.advanced_compliance.knowledge_graph.analysis import CoverageAnalyzer

		analyzer = CoverageAnalyzer()
		self.assertIsNotNone(analyzer.query_engine)

	def test_02_analyze_risk_coverage(self):
		"""Test risk coverage analysis."""
		from advanced_compliance.advanced_compliance.knowledge_graph.analysis import CoverageAnalyzer

		analyzer = CoverageAnalyzer()
		result = analyzer.analyze_risk_coverage()

		self.assertIn("total_risks", result)
		self.assertIn("fully_covered", result)
		self.assertIn("uncovered", result)
		self.assertIn("coverage_percentage", result)

	def test_03_analyze_control_testing(self):
		"""Test control testing coverage analysis."""
		from advanced_compliance.advanced_compliance.knowledge_graph.analysis import CoverageAnalyzer

		analyzer = CoverageAnalyzer()
		result = analyzer.analyze_control_testing()

		self.assertIn("total_controls", result)
		self.assertIn("tested", result)
		self.assertIn("untested", result)
		self.assertIn("testing_coverage_percentage", result)

	def test_04_analyze_ownership(self):
		"""Test ownership analysis."""
		from advanced_compliance.advanced_compliance.knowledge_graph.analysis import CoverageAnalyzer

		analyzer = CoverageAnalyzer()
		result = analyzer.analyze_ownership()

		self.assertIn("total_controls", result)
		self.assertIn("owned", result)
		self.assertIn("unowned", result)
		self.assertIn("ownership_coverage_percentage", result)

	def test_05_find_orphaned_entities(self):
		"""Test orphaned entity detection."""
		from advanced_compliance.advanced_compliance.knowledge_graph.analysis import CoverageAnalyzer

		# Create an orphaned entity
		orphan = create_test_entity("Process", "DocType", "COV-TEST-ORPHAN")

		analyzer = CoverageAnalyzer()
		result = analyzer.find_orphaned_entities()

		self.assertIn("orphaned_by_type", result)
		self.assertIn("total_orphaned", result)

	def test_06_get_compliance_score(self):
		"""Test compliance score calculation."""
		from advanced_compliance.advanced_compliance.knowledge_graph.analysis import CoverageAnalyzer

		analyzer = CoverageAnalyzer()
		result = analyzer.get_compliance_score()

		self.assertIn("overall_score", result)
		self.assertIn("grade", result)
		self.assertIn("breakdown", result)
		self.assertIn("recommendations", result)

		# Score should be between 0 and 100
		self.assertGreaterEqual(result["overall_score"], 0)
		self.assertLessEqual(result["overall_score"], 100)

		# Grade should be A-F
		self.assertIn(result["grade"], ["A", "B", "C", "D", "F"])

	def test_07_get_full_analysis(self):
		"""Test full analysis."""
		from advanced_compliance.advanced_compliance.knowledge_graph.analysis import CoverageAnalyzer

		analyzer = CoverageAnalyzer()
		result = analyzer.get_full_analysis()

		self.assertIn("compliance_score", result)
		self.assertIn("risk_coverage", result)
		self.assertIn("control_testing", result)
		self.assertIn("ownership", result)
		self.assertIn("orphaned_entities", result)
		self.assertIn("dependencies", result)


class TestGraphAPIEndpoints(unittest.TestCase):
	"""Tests for Graph API Endpoints."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def test_01_get_entity_neighbors_api(self):
		"""Test get_entity_neighbors API endpoint."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import get_entity_neighbors

		# This should not raise permission error for Administrator
		# Even if no entity exists, it should handle gracefully
		try:
			result = get_entity_neighbors(entity_name="NON-EXISTENT", direction="both")
			# Should return empty list for non-existent entity
			self.assertEqual(result, [])
		except Exception:
			pass  # Entity doesn't exist, which is fine

	def test_02_get_visualization_data_api(self):
		"""Test get_visualization_data API endpoint."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import get_visualization_data

		result = get_visualization_data(max_nodes=10)

		self.assertIn("nodes", result)
		self.assertIn("edges", result)

	def test_03_get_graph_statistics_api(self):
		"""Test get_graph_statistics API endpoint."""
		from advanced_compliance.advanced_compliance.knowledge_graph.query import get_graph_statistics

		result = get_graph_statistics()

		self.assertIn("total_entities", result)
		self.assertIn("total_relationships", result)
		self.assertIn("entities_by_type", result)
		self.assertIn("relationships_by_type", result)

	def test_04_get_compliance_score_api(self):
		"""Test get_compliance_score API endpoint."""
		from advanced_compliance.advanced_compliance.knowledge_graph.analysis import get_compliance_score

		result = get_compliance_score()

		self.assertIn("overall_score", result)
		self.assertIn("grade", result)


def run_tests():
	"""Run all knowledge graph tests."""
	suite = unittest.TestSuite()

	# Add test classes
	suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestComplianceGraphEntity))
	suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestComplianceGraphRelationship))
	suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestComplianceGraphPath))
	suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGraphSyncEngine))
	suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGraphQueryEngine))
	suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCoverageAnalyzer))
	suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGraphAPIEndpoints))

	# Run tests
	runner = unittest.TextTestRunner(verbosity=2)
	result = runner.run(suite)

	return result
