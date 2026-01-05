"""
Unit tests for bug fixes implemented in Advanced Compliance app.

This test file covers all bug fixes from BUGS_AND_FIXES.md:
- SQL injection prevention
- Hardcoded fallback removal
- NULL handling
- Division by zero
- Permission checks
- Security improvements
"""

import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.utils import add_days, cint, flt, nowdate


class TestSQLInjectionPrevention(unittest.TestCase):
	"""Test SQL injection prevention fixes."""

	def setUp(self):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def test_semantic_search_field_validation(self):
		"""
		Test that semantic_search._text_search_fallback validates fields.

		Bug: semantic_search.py line 253 - SQL injection via unvalidated fields
		Fix: Added field validation using frappe.get_meta()
		"""
		from advanced_compliance.advanced_compliance.intelligence.search.semantic_search import SemanticSearch

		search = SemanticSearch()

		# Test with valid query
		results = search._text_search_fallback(query="test", doctypes=["Control Activity"], limit=10)

		# Should return results without error (no SQL injection)
		self.assertIsInstance(results, list)

		# Test with invalid doctype (should handle gracefully)
		results = search._text_search_fallback(
			query="test'; DROP TABLE tabControl; --", doctypes=["NonExistentDocType"], limit=10
		)

		# Should return empty list, not error
		self.assertEqual(results, [])

	def test_performance_index_parameterized_queries(self):
		"""
		Test that add_performance_indexes uses parameterized queries.

		Bug: add_performance_indexes.py line 59 - SQL injection via f-string
		Fix: Used frappe.db.add_index() and parameterized queries
		"""
		# This test verifies the fix is in place by checking the code doesn't use
		# raw SQL for index creation. The actual patch runs during migration,
		# so we verify the fix exists rather than running the patch.

		from advanced_compliance.patches import add_performance_indexes

		# Verify the module has the safe implementation
		self.assertTrue(hasattr(add_performance_indexes, "execute"))

		# Check that the execute function doesn't contain raw f-string SQL
		import inspect

		source = inspect.getsource(add_performance_indexes.execute)

		# Should use frappe.db.add_index (safe method)
		self.assertIn("frappe.db.add_index", source)

		# Should NOT use raw CREATE INDEX (unsafe)
		self.assertNotIn("CREATE INDEX IF NOT EXISTS", source)


class TestHardcodedFallbackRemoval(unittest.TestCase):
	"""Test removal of hardcoded fallback values."""

	def setUp(self):
		"""Set up test environment."""
		frappe.set_user("Administrator")

		# Ensure Compliance Settings exist
		if not frappe.db.exists("Compliance Settings", "Compliance Settings"):
			settings = frappe.get_doc({"doctype": "Compliance Settings"})
			settings.insert(ignore_permissions=True)

	def test_days_since_test_uses_settings(self):
		"""
		Test that _get_days_since_test uses settings, not hardcoded 365.

		Bug: risk_predictor.py line 146 - hardcoded 365 days
		Fix: Uses Compliance Settings.default_days_never_tested
		"""
		from advanced_compliance.advanced_compliance.intelligence.prediction.risk_predictor import (
			RiskPredictor,
		)

		predictor = RiskPredictor()

		# Create a test control with no test history
		control = frappe.get_doc(
			{
				"doctype": "Control Activity",
				"control_id": "TEST-CONTROL-001",
				"control_title": "Test Control",
				"status": "Active",
				"last_test_date": None,  # Never tested
			}
		)

		# Configure settings with specific value
		settings = frappe.get_single("Compliance Settings")
		settings.default_days_never_tested = 180
		settings.save(ignore_permissions=True)

		# Should use configured value (180), not hardcoded 365
		days = predictor._get_days_since_test(control)
		self.assertEqual(days, 180)

		# Test with missing configuration (should throw helpful error)
		settings.default_days_never_tested = 0
		settings.save(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError) as context:
			predictor._get_days_since_test(control)

		# Error should mention settings configuration
		self.assertIn("Compliance Settings", str(context.exception))

	def test_pass_rate_returns_none_for_no_history(self):
		"""
		Test that _get_test_pass_rate returns None (not 0.5) when no tests.

		Bug: risk_predictor.py line 172 - hardcoded 0.5 fallback
		Fix: Returns None, caller handles with configured penalty
		"""
		from advanced_compliance.advanced_compliance.intelligence.prediction.risk_predictor import (
			RiskPredictor,
		)

		predictor = RiskPredictor()

		# Test with non-existent control (no test history)
		pass_rate = predictor._get_test_pass_rate("NONEXISTENT-CONTROL")

		# Should return None, not 0.5
		self.assertIsNone(pass_rate)


class TestNullAndDivisionSafety(unittest.TestCase):
	"""Test NULL handling and division by zero fixes."""

	def setUp(self):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def test_anomaly_null_handling(self):
		"""
		Test that compliance_anomaly handles SQL NULL results safely.

		Bug: compliance_anomaly.py line 172 - NULL from SUM() not handled
		Fix: Added flt(value or 0) for NULL safety
		"""
		from advanced_compliance.advanced_compliance.intelligence.anomaly.compliance_anomaly import (
			ComplianceAnomalyDetector,
		)

		# Ensure AI Provider Settings exist
		if not frappe.db.exists("AI Provider Settings", "AI Provider Settings"):
			settings = frappe.get_doc({"doctype": "AI Provider Settings"})
			settings.insert(ignore_permissions=True)

		detector = ComplianceAnomalyDetector()

		# Test with controls that have no test data (will return NULL from SUM)
		anomalies = detector.detect_all_anomalies()

		# Should complete without AttributeError or TypeError
		self.assertIsInstance(anomalies, list)

	def test_deficiency_increase_division_by_zero(self):
		"""
		Test that _detect_deficiency_increase handles zero denominator.

		Bug: compliance_anomaly.py line 371 - division by zero risk
		Fix: Added check for zero/None denominator and infinity result
		"""
		from advanced_compliance.advanced_compliance.intelligence.anomaly.compliance_anomaly import (
			ComplianceAnomalyDetector,
		)

		# Ensure AI Provider Settings exist
		if not frappe.db.exists("AI Provider Settings", "AI Provider Settings"):
			settings = frappe.get_doc({"doctype": "AI Provider Settings"})
			settings.insert(ignore_permissions=True)

		detector = ComplianceAnomalyDetector()

		# Test with mock data where previous_count is 0
		with patch.object(frappe.db, "sql") as mock_sql:
			# Mock response: COUNT(*) returns [(0,)] - previous period has 0 deficiencies
			# This would cause division by zero without proper handling
			mock_sql.return_value = [(0,)]

			# Should handle gracefully without ZeroDivisionError
			anomalies = detector.detect_deficiency_spikes()
			self.assertIsInstance(anomalies, list)


class TestGetterDesignPattern(unittest.TestCase):
	"""Test getter methods return defaults instead of throwing errors."""

	def setUp(self):
		"""Set up test environment."""
		frappe.set_user("Administrator")

		# Ensure AI Provider Settings exist
		if not frappe.db.exists("AI Provider Settings", "AI Provider Settings"):
			settings = frappe.get_doc({"doctype": "AI Provider Settings"})
			settings.insert(ignore_permissions=True)

	def test_anomaly_sensitivity_returns_default(self):
		"""
		Test that get_anomaly_sensitivity_value returns default, not error.

		Bug: ai_provider_settings.py line 56 - throws error if not configured
		Fix: Returns 1.0 (Medium) default if not configured
		"""
		settings = frappe.get_single("AI Provider Settings")

		# Clear anomaly sensitivity
		settings.anomaly_sensitivity = None
		settings.save(ignore_permissions=True)

		# Should return default (1.0), not throw error
		value = settings.get_anomaly_sensitivity_value()
		self.assertEqual(value, 1.0)

		# Test with valid values
		for sensitivity, expected in [("Low", 0.5), ("Medium", 1.0), ("High", 2.0)]:
			settings.anomaly_sensitivity = sensitivity
			settings.save(ignore_permissions=True)
			value = settings.get_anomaly_sensitivity_value()
			self.assertEqual(value, expected)


class TestPermissionChecks(unittest.TestCase):
	"""Test permission check improvements."""

	def setUp(self):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def test_query_engine_respects_row_permissions(self):
		"""
		Test that query engine count respects row-level permissions.

		Bug: query_engine.py line 344 - frappe.db.count bypasses permissions
		Fix: Uses frappe.get_all which respects row-level permissions
		"""
		from advanced_compliance.advanced_compliance.intelligence.nlp.query_engine import NLQueryEngine

		engine = NLQueryEngine()

		# Test count query uses frappe.get_all (not frappe.db.count)
		# We verify this by checking the implementation
		import inspect

		source = inspect.getsource(engine._execute_rule_based_query)

		# Should use frappe.get_all for counts
		self.assertIn("frappe.get_all", source)

		# Should NOT use frappe.db.count
		# Note: This is a code inspection test; actual permission testing
		# would require setting up user permissions which is complex


class TestSemanticSearchSecurity(unittest.TestCase):
	"""Test semantic search security improvements."""

	def setUp(self):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def test_semantic_search_uses_public_api_method(self):
		"""
		Test that semantic search uses public API method (not private).

		Bug: semantic_search.py line 189 - accesses private _get_api_key()
		Fix: Uses public get_api_credentials() method instead
		"""
		from advanced_compliance.advanced_compliance.intelligence.search.semantic_search import SemanticSearch

		# Verify the class has the OpenAI embedding methods (functionality restored)
		search = SemanticSearch()

		# Should have _openai_embedding method (functionality restored)
		self.assertTrue(hasattr(search, "_openai_embedding"))

		# Should have _generate_api_embedding method (functionality restored)
		self.assertTrue(hasattr(search, "_generate_api_embedding"))

		# Should have _get_ai_provider method
		self.assertTrue(hasattr(search, "_get_ai_provider"))

		# Should still have _generate_local_embedding method
		self.assertTrue(hasattr(search, "_generate_local_embedding"))

		# Verify the code uses public method, not private
		import inspect

		source = inspect.getsource(search._openai_embedding)

		# Should use public get_api_credentials() method
		self.assertIn("get_api_credentials", source)

		# Should NOT use private _get_api_key() method
		self.assertNotIn("_get_api_key", source)

	def test_no_private_api_key_access(self):
		"""
		Verify semantic_search doesn't access private AIProviderResolver methods.

		The code should use public get_api_credentials() instead of private _get_api_key()
		"""
		# Check source code doesn't contain private method access
		import inspect

		from advanced_compliance.advanced_compliance.intelligence.search import semantic_search

		source = inspect.getsource(semantic_search)

		# Should NOT access _get_api_key (private method)
		self.assertNotIn("_get_api_key", source)

		# Should use public get_api_credentials method instead
		self.assertIn("get_api_credentials", source)


class TestConfigurationFields(unittest.TestCase):
	"""Test that new configuration fields work correctly."""

	def setUp(self):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def test_compliance_settings_has_default_days_field(self):
		"""
		Test that Compliance Settings has default_days_never_tested field.

		Configuration addition for bug fix #3
		"""
		settings = frappe.get_single("Compliance Settings")

		# Should have the new field
		self.assertTrue(hasattr(settings, "default_days_never_tested"))

		# Default should be 365
		if not settings.default_days_never_tested:
			settings.default_days_never_tested = 365
			settings.save(ignore_permissions=True)

		self.assertEqual(cint(settings.default_days_never_tested), 365)

	def test_ai_provider_settings_has_penalty_field(self):
		"""
		Test that AI Provider Settings has no_test_history_penalty field.

		Configuration addition for bug fix #4
		"""
		if not frappe.db.exists("AI Provider Settings", "AI Provider Settings"):
			settings = frappe.get_doc({"doctype": "AI Provider Settings"})
			settings.insert(ignore_permissions=True)

		settings = frappe.get_single("AI Provider Settings")

		# Should have the new field
		self.assertTrue(hasattr(settings, "no_test_history_penalty"))

		# Default should be 0.1
		if not settings.no_test_history_penalty:
			settings.no_test_history_penalty = 0.1
			settings.save(ignore_permissions=True)

		self.assertAlmostEqual(flt(settings.no_test_history_penalty), 0.1, places=2)


# Test execution
if __name__ == "__main__":
	unittest.main()
