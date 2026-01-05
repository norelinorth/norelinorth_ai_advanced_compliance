"""
Test Evidence Capture System.

Tests for automatic evidence capture from ERPNext documents.
Follows standard Frappe testing patterns.
"""

import json
import unittest

import frappe
from frappe.utils import add_days, flt, now_datetime, nowdate


def get_or_create_test_control(control_name):
	"""Get or create a test control activity."""
	if frappe.db.exists("Control Activity", {"control_name": control_name}):
		return frappe.db.get_value("Control Activity", {"control_name": control_name}, "name")

	# Ensure Financial Reporting category exists
	if not frappe.db.exists("Control Category", "Financial Reporting"):
		category = frappe.get_doc(
			{
				"doctype": "Control Category",
				"category_name": "Financial Reporting",
				"description": "Controls related to financial reporting and disclosure",
			}
		)
		category.insert(ignore_permissions=True)
		frappe.db.commit()

	control = frappe.get_doc(
		{
			"doctype": "Control Activity",
			"control_name": control_name,
			"description": f"Test control: {control_name}",
			"control_category": "Financial Reporting",
			"frequency": "Monthly",
			"control_type": "Detective",
			"automation_level": "Manual",
			"control_owner": "Administrator",
			"status": "Active",
		}
	)
	control.insert(ignore_permissions=True)
	frappe.db.commit()
	return control.name


class TestEvidenceCaptureCondition(unittest.TestCase):
	"""Tests for Evidence Capture Condition child table."""

	def test_condition_operators(self):
		"""Test that all operators are available."""
		meta = frappe.get_meta("Evidence Capture Condition")
		operator_field = meta.get_field("operator")

		expected_operators = ["=", "!=", ">", ">=", "<", "<=", "in", "not in"]
		available_operators = operator_field.options.split("\n")

		for op in expected_operators:
			self.assertIn(op, available_operators)


class TestEvidenceLinkedDocument(unittest.TestCase):
	"""Tests for Evidence Linked Document child table."""

	def test_dynamic_link_configuration(self):
		"""Test that dynamic link is properly configured."""
		meta = frappe.get_meta("Evidence Linked Document")
		document_name_field = meta.get_field("document_name")

		self.assertEqual(document_name_field.fieldtype, "Dynamic Link")
		self.assertEqual(document_name_field.options, "document_type")


class TestEvidenceCaptureRule(unittest.TestCase):
	"""Tests for Evidence Capture Rule DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test fixtures."""
		frappe.set_user("Administrator")
		cls.test_control = get_or_create_test_control("_Test Evidence Control")

	def test_create_capture_rule(self):
		"""Test creating a basic capture rule."""
		rule = frappe.get_doc(
			{
				"doctype": "Evidence Capture Rule",
				"rule_name": "_Test Capture Rule",
				"enabled": 1,
				"control_activity": self.test_control,
				"source_doctype": "Sales Invoice",
				"trigger_event": "on_submit",
				"capture_document_pdf": 1,
			}
		)
		rule.insert(ignore_permissions=True)

		self.assertTrue(rule.name)
		self.assertEqual(rule.source_doctype, "Sales Invoice")

		# Cleanup
		rule.delete(ignore_permissions=True)

	def test_capture_rule_with_conditions(self):
		"""Test capture rule with filter conditions."""
		rule = frappe.get_doc(
			{
				"doctype": "Evidence Capture Rule",
				"rule_name": "_Test Rule With Conditions",
				"enabled": 1,
				"control_activity": self.test_control,
				"source_doctype": "Sales Invoice",
				"trigger_event": "on_submit",
				"conditions": [
					{"field_name": "grand_total", "operator": ">", "value": "10000"},
					{"field_name": "status", "operator": "=", "value": "Submitted"},
				],
			}
		)
		rule.insert(ignore_permissions=True)

		self.assertEqual(len(rule.conditions), 2)

		# Cleanup
		rule.delete(ignore_permissions=True)

	def test_invalid_source_doctype(self):
		"""Test that invalid source doctype raises error."""
		rule = frappe.get_doc(
			{
				"doctype": "Evidence Capture Rule",
				"rule_name": "_Test Invalid DocType Rule",
				"enabled": 1,
				"control_activity": self.test_control,
				"source_doctype": "NonExistent DocType",
				"trigger_event": "on_submit",
			}
		)

		with self.assertRaises(frappe.ValidationError):
			rule.insert(ignore_permissions=True)

	def test_trigger_event_options(self):
		"""Test that all trigger events are available."""
		meta = frappe.get_meta("Evidence Capture Rule")
		trigger_field = meta.get_field("trigger_event")

		expected_events = ["on_submit", "on_update", "on_cancel"]
		available_events = trigger_field.options.split("\n")

		for event in expected_events:
			self.assertIn(event, available_events)


class TestControlEvidenceDocType(unittest.TestCase):
	"""Tests for Control Evidence DocType metadata and fields."""

	def test_control_evidence_fields_exist(self):
		"""Test that Control Evidence has all required fields."""
		meta = frappe.get_meta("Control Evidence")

		required_fields = [
			"control_activity",
			"source_doctype",
			"source_name",
			"captured_at",
			"evidence_hash",
			"document_snapshot",
			"workflow_log",
			"version_history",
			"comments_log",
		]

		for field_name in required_fields:
			field = meta.get_field(field_name)
			self.assertIsNotNone(field, f"Field {field_name} should exist")

	def test_evidence_naming_series(self):
		"""Test that evidence uses correct naming series."""
		meta = frappe.get_meta("Control Evidence")
		naming_field = meta.get_field("naming_series")

		self.assertIsNotNone(naming_field)
		self.assertIn("EVD-", naming_field.options)


class TestControlEvidenceCreation(unittest.TestCase):
	"""Tests for creating Control Evidence documents."""

	@classmethod
	def setUpClass(cls):
		"""Set up test fixtures."""
		frappe.set_user("Administrator")
		cls.test_control = get_or_create_test_control("_Test Evidence Control 2")

	def test_create_evidence_basic(self):
		"""Test creating basic control evidence without links."""
		evidence = frappe.get_doc(
			{
				"doctype": "Control Evidence",
				"control_activity": self.test_control,
				"source_doctype": "DocType",
				"source_name": "Sales Invoice",
				"source_owner": "Administrator",
			}
		)
		evidence.flags.ignore_links = True
		evidence.insert(ignore_permissions=True)

		self.assertTrue(evidence.name)
		self.assertTrue(evidence.captured_at)
		self.assertTrue(evidence.evidence_hash)
		self.assertTrue(evidence.evidence_hash.startswith("sha256:"))

		# Cleanup - use force to handle linked graph entities
		frappe.delete_doc("Control Evidence", evidence.name, force=True)

	def test_evidence_hash_format(self):
		"""Test that evidence hash is generated in correct format."""
		evidence = frappe.get_doc(
			{
				"doctype": "Control Evidence",
				"control_activity": self.test_control,
				"source_doctype": "DocType",
				"source_name": "Purchase Invoice",
				"source_owner": "Administrator",
				"workflow_log": json.dumps([{"action": "Submit", "user": "Administrator"}]),
			}
		)
		evidence.flags.ignore_links = True
		evidence.insert(ignore_permissions=True)

		# Hash should be SHA-256 format
		self.assertTrue(evidence.evidence_hash.startswith("sha256:"))
		self.assertEqual(len(evidence.evidence_hash), 71)  # "sha256:" + 64 hex chars

		# Cleanup - use force to handle linked graph entities
		frappe.delete_doc("Control Evidence", evidence.name, force=True)

	def test_evidence_summary_auto_generated(self):
		"""Test that evidence summary is auto-generated."""
		evidence = frappe.get_doc(
			{
				"doctype": "Control Evidence",
				"control_activity": self.test_control,
				"source_doctype": "DocType",
				"source_name": "Journal Entry",
				"source_owner": "Administrator",
				"document_snapshot": "/files/test.pdf",
			}
		)
		evidence.flags.ignore_links = True
		evidence.insert(ignore_permissions=True)

		self.assertTrue(evidence.evidence_summary)
		self.assertIn("Journal Entry", evidence.evidence_summary)
		self.assertIn("PDF snapshot captured", evidence.evidence_summary)

		# Cleanup - use force to handle linked graph entities
		frappe.delete_doc("Control Evidence", evidence.name, force=True)

	def test_evidence_integrity_verification(self):
		"""Test evidence integrity check method."""
		evidence = frappe.get_doc(
			{
				"doctype": "Control Evidence",
				"control_activity": self.test_control,
				"source_doctype": "DocType",
				"source_name": "Stock Entry",
				"source_owner": "Administrator",
			}
		)
		evidence.flags.ignore_links = True
		evidence.insert(ignore_permissions=True)

		# Integrity should pass for unmodified evidence
		result = evidence.verify_integrity()
		self.assertTrue(result)

		# Cleanup - use force to handle linked graph entities
		frappe.delete_doc("Control Evidence", evidence.name, force=True)


class TestEvidenceCaptureEngine(unittest.TestCase):
	"""Tests for the evidence capture engine (capture.py)."""

	def test_evaluate_single_condition_equals(self):
		"""Test equals operator."""
		from advanced_compliance.advanced_compliance.evidence.capture import evaluate_single_condition

		self.assertTrue(evaluate_single_condition("Active", "=", "Active"))
		self.assertFalse(evaluate_single_condition("Active", "=", "Inactive"))

	def test_evaluate_single_condition_not_equals(self):
		"""Test not equals operator."""
		from advanced_compliance.advanced_compliance.evidence.capture import evaluate_single_condition

		self.assertTrue(evaluate_single_condition("Active", "!=", "Inactive"))
		self.assertFalse(evaluate_single_condition("Active", "!=", "Active"))

	def test_evaluate_single_condition_greater_than(self):
		"""Test greater than operator."""
		from advanced_compliance.advanced_compliance.evidence.capture import evaluate_single_condition

		self.assertTrue(evaluate_single_condition(100, ">", "50"))
		self.assertFalse(evaluate_single_condition(50, ">", "100"))

	def test_evaluate_single_condition_less_than(self):
		"""Test less than operator."""
		from advanced_compliance.advanced_compliance.evidence.capture import evaluate_single_condition

		self.assertTrue(evaluate_single_condition(50, "<", "100"))
		self.assertFalse(evaluate_single_condition(100, "<", "50"))

	def test_evaluate_single_condition_greater_equal(self):
		"""Test greater than or equal operator."""
		from advanced_compliance.advanced_compliance.evidence.capture import evaluate_single_condition

		self.assertTrue(evaluate_single_condition(100, ">=", "100"))
		self.assertTrue(evaluate_single_condition(101, ">=", "100"))
		self.assertFalse(evaluate_single_condition(99, ">=", "100"))

	def test_evaluate_single_condition_less_equal(self):
		"""Test less than or equal operator."""
		from advanced_compliance.advanced_compliance.evidence.capture import evaluate_single_condition

		self.assertTrue(evaluate_single_condition(100, "<=", "100"))
		self.assertTrue(evaluate_single_condition(99, "<=", "100"))
		self.assertFalse(evaluate_single_condition(101, "<=", "100"))

	def test_evaluate_single_condition_in_list(self):
		"""Test in operator."""
		from advanced_compliance.advanced_compliance.evidence.capture import evaluate_single_condition

		self.assertTrue(evaluate_single_condition("USD", "in", "USD, EUR, GBP"))
		self.assertFalse(evaluate_single_condition("JPY", "in", "USD, EUR, GBP"))

	def test_evaluate_single_condition_not_in_list(self):
		"""Test not in operator."""
		from advanced_compliance.advanced_compliance.evidence.capture import evaluate_single_condition

		self.assertTrue(evaluate_single_condition("JPY", "not in", "USD, EUR, GBP"))
		self.assertFalse(evaluate_single_condition("USD", "not in", "USD, EUR, GBP"))

	def test_evaluate_single_condition_none_value(self):
		"""Test handling of None values."""
		from advanced_compliance.advanced_compliance.evidence.capture import evaluate_single_condition

		self.assertTrue(evaluate_single_condition(None, "=", ""))
		self.assertFalse(evaluate_single_condition(None, "=", "value"))

	def test_evaluate_single_condition_invalid_operator(self):
		"""Test handling of invalid operator."""
		from advanced_compliance.advanced_compliance.evidence.capture import evaluate_single_condition

		result = evaluate_single_condition("test", "invalid_op", "test")
		self.assertFalse(result)

	def test_get_applicable_rules(self):
		"""Test retrieving applicable capture rules."""
		from advanced_compliance.advanced_compliance.evidence.capture import get_applicable_rules

		# This should not raise an error even if no rules exist
		rules = get_applicable_rules("Sales Invoice", "on_submit")
		self.assertIsInstance(rules, list)

	def test_get_default_print_format(self):
		"""Test getting default print format."""
		from advanced_compliance.advanced_compliance.evidence.capture import get_default_print_format

		# Should return "Standard" if no default is set
		print_format = get_default_print_format("Sales Invoice")
		self.assertIsNotNone(print_format)


class TestEvidenceCaptureIntegration(unittest.TestCase):
	"""Integration tests for evidence capture with Compliance Settings."""

	@classmethod
	def setUpClass(cls):
		"""Set up test fixtures."""
		frappe.set_user("Administrator")

		# Ensure Compliance Settings exists and is configured
		settings = frappe.get_single("Compliance Settings")
		cls.original_enabled = settings.enable_compliance_features
		settings.enable_compliance_features = 0
		settings.save(ignore_permissions=True)
		frappe.db.commit()

	def test_capture_disabled_when_features_off(self):
		"""Test that capture doesn't run when compliance features disabled."""
		from advanced_compliance.advanced_compliance.evidence.capture import on_document_submit

		# Create a mock document
		class MockDoc:
			doctype = "Sales Invoice"
			name = "SINV-MOCK-001"

		# Should return without error when disabled
		result = on_document_submit(MockDoc(), "on_submit")
		self.assertIsNone(result)

	def test_capture_runs_when_features_enabled(self):
		"""Test that capture runs when compliance features enabled."""
		settings = frappe.get_single("Compliance Settings")
		settings.enable_compliance_features = 1
		settings.save(ignore_permissions=True)

		from advanced_compliance.advanced_compliance.evidence.capture import get_applicable_rules

		# Should be able to query rules when enabled
		rules = get_applicable_rules("Sales Invoice", "on_submit")
		self.assertIsInstance(rules, list)

		# Restore
		settings.enable_compliance_features = 0
		settings.save(ignore_permissions=True)

	@classmethod
	def tearDownClass(cls):
		"""Restore original settings."""
		settings = frappe.get_single("Compliance Settings")
		settings.enable_compliance_features = cls.original_enabled
		settings.save(ignore_permissions=True)
		frappe.db.commit()


class TestManualEvidenceCapture(unittest.TestCase):
	"""Tests for manual evidence capture API."""

	@classmethod
	def setUpClass(cls):
		"""Set up test fixtures."""
		frappe.set_user("Administrator")
		cls.test_control = get_or_create_test_control("_Test Manual Evidence Control")

	def test_manual_capture_permission_check(self):
		"""Test that manual capture requires permission."""
		from advanced_compliance.advanced_compliance.evidence.capture import manually_capture_evidence

		# Switch to user without permission
		frappe.set_user("Guest")

		# Should raise ValidationError (which is what frappe.throw raises)
		with self.assertRaises(frappe.ValidationError):
			manually_capture_evidence("Sales Invoice", "SINV-00001", self.test_control)

		# Restore
		frappe.set_user("Administrator")

	def tearDown(self):
		"""Clean up after each test."""
		frappe.set_user("Administrator")


class TestEvidenceGetForControl(unittest.TestCase):
	"""Tests for getting evidence for a control activity."""

	@classmethod
	def setUpClass(cls):
		"""Set up test fixtures."""
		frappe.set_user("Administrator")
		cls.test_control = get_or_create_test_control("_Test Evidence Get Control")

	def test_get_evidence_for_control_method(self):
		"""Test static method to get evidence for control."""
		from advanced_compliance.advanced_compliance.doctype.control_evidence.control_evidence import (
			ControlEvidence,
		)

		# Create test evidence
		evidence = frappe.get_doc(
			{
				"doctype": "Control Evidence",
				"control_activity": self.test_control,
				"source_doctype": "DocType",
				"source_name": "User",
				"source_owner": "Administrator",
			}
		)
		evidence.flags.ignore_links = True
		evidence.insert(ignore_permissions=True)
		frappe.db.commit()

		# Retrieve evidence
		evidence_list = ControlEvidence.get_evidence_for_control(self.test_control)
		self.assertGreaterEqual(len(evidence_list), 1)

		# Cleanup - use force to handle linked graph entities
		frappe.delete_doc("Control Evidence", evidence.name, force=True)


def run_tests():
	"""Run all evidence capture tests."""
	unittest.main(module=__name__, exit=False, verbosity=2)
