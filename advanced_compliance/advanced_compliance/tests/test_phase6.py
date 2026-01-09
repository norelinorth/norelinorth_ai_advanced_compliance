# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Tests for Phase 6: Polish & Marketplace

Test Coverage:
- Performance utilities
- Caching system
- Formatting utilities
- Help system
- Demo data generation
"""

import unittest

import frappe
from frappe.utils import add_days, nowdate


class TestCacheUtilities(unittest.TestCase):
	"""Tests for caching utilities."""

	def setUp(self):
		"""Set up before each test."""
		frappe.set_user("Administrator")

	def test_get_cached_with_generator(self):
		"""Test caching with generator function."""
		from advanced_compliance.advanced_compliance.utils.cache import get_cached, invalidate_cache

		# Test that get_cached returns valid values from generator
		def generator():
			return {"test": "value", "data": [1, 2, 3]}

		result = get_cached("test_cache_basic", generator, ttl=60)

		self.assertIn("test", result)
		self.assertEqual(result["test"], "value")
		self.assertEqual(result["data"], [1, 2, 3])

		# Clean up
		invalidate_cache("test_cache_basic")

	def test_invalidate_cache(self):
		"""Test cache invalidation."""
		from advanced_compliance.advanced_compliance.utils.cache import get_cached, invalidate_cache

		call_count = [0]

		def generator():
			call_count[0] += 1
			return {"count": call_count[0]}

		# First call
		result1 = get_cached("test_key_2", generator, ttl=60)
		self.assertEqual(result1["count"], 1)

		# Invalidate cache
		invalidate_cache("test_key_2")

		# Second call should execute generator again
		result2 = get_cached("test_key_2", generator, ttl=60)
		self.assertEqual(result2["count"], 2)


class TestOptimizations(unittest.TestCase):
	"""Tests for query optimization utilities."""

	def setUp(self):
		"""Set up before each test."""
		frappe.set_user("Administrator")

	def test_get_compliance_summary(self):
		"""Test compliance summary query."""
		from advanced_compliance.advanced_compliance.utils.optimizations import get_compliance_summary

		summary = get_compliance_summary()

		self.assertIn("active_controls", summary)
		self.assertIn("key_controls", summary)
		self.assertIn("active_risks", summary)
		self.assertIn("open_deficiencies", summary)
		self.assertIn("pending_tests", summary)
		self.assertIn("new_updates", summary)

		# All values should be non-negative integers
		for key, value in summary.items():
			self.assertIsInstance(value, int)
			self.assertGreaterEqual(value, 0)


class TestFormatting(unittest.TestCase):
	"""Tests for formatting utilities."""

	def test_format_for_locale_date(self):
		"""Test date formatting."""
		from advanced_compliance.advanced_compliance.utils.formatting import format_for_locale

		result = format_for_locale(nowdate(), "date")
		self.assertIsNotNone(result)
		self.assertIsInstance(result, str)

	def test_format_for_locale_percent(self):
		"""Test percentage formatting."""
		from advanced_compliance.advanced_compliance.utils.formatting import format_for_locale

		result = format_for_locale(85.5, "percent")
		self.assertEqual(result, "85.5%")

	def test_format_risk_score(self):
		"""Test risk score formatting."""
		from advanced_compliance.advanced_compliance.utils.formatting import format_risk_score

		# Test critical
		critical = format_risk_score(25)
		self.assertEqual(critical["color"], "red")
		self.assertEqual(critical["label"], "Critical")

		# Test high
		high = format_risk_score(15)
		self.assertEqual(high["color"], "orange")

		# Test medium
		medium = format_risk_score(10)
		self.assertEqual(medium["color"], "yellow")

		# Test low
		low = format_risk_score(5)
		self.assertEqual(low["color"], "blue")

		# Test very low
		very_low = format_risk_score(2)
		self.assertEqual(very_low["color"], "green")

	def test_format_control_status(self):
		"""Test control status formatting."""
		from advanced_compliance.advanced_compliance.utils.formatting import format_control_status

		result = format_control_status("Active")
		self.assertEqual(result["color"], "green")
		self.assertEqual(result["status"], "Active")

	def test_format_days_until(self):
		"""Test days until date formatting."""
		from advanced_compliance.advanced_compliance.utils.formatting import format_days_until

		# Test future date
		future = format_days_until(add_days(nowdate(), 30))
		self.assertEqual(future["days"], 30)
		self.assertIn(future["color"], ["green", "yellow"])

		# Test overdue date
		past = format_days_until(add_days(nowdate(), -5))
		self.assertEqual(past["days"], 5)
		self.assertEqual(past["color"], "red")

		# Test today
		today = format_days_until(nowdate())
		self.assertEqual(today["days"], 0)
		self.assertEqual(today["color"], "red")

	def test_format_percentage_change(self):
		"""Test percentage change formatting."""
		from advanced_compliance.advanced_compliance.utils.formatting import format_percentage_change

		# Test increase
		increase = format_percentage_change(110, 100)
		self.assertEqual(increase["direction"], "up")
		self.assertEqual(increase["color"], "green")

		# Test decrease
		decrease = format_percentage_change(90, 100)
		self.assertEqual(decrease["direction"], "down")
		self.assertEqual(decrease["color"], "red")

		# Test no change
		same = format_percentage_change(100, 100)
		self.assertEqual(same["direction"], "neutral")


class TestHelpSystem(unittest.TestCase):
	"""Tests for in-app help system."""

	def setUp(self):
		"""Set up before each test."""
		frappe.set_user("Administrator")

	def test_get_help_doctype(self):
		"""Test getting help for a DocType."""
		from advanced_compliance.advanced_compliance.help import get_help

		help_data = get_help("Control Activity")

		self.assertIn("title", help_data)
		self.assertIn("description", help_data)
		self.assertIn("tips", help_data)
		self.assertTrue(len(help_data["tips"]) > 0)

	def test_get_help_field(self):
		"""Test getting help for a specific field."""
		from advanced_compliance.advanced_compliance.help import get_help

		help_data = get_help("Control Activity", "control_name")

		self.assertIn("title", help_data)
		self.assertIn("description", help_data)
		self.assertEqual(help_data["title"], "control_name")

	def test_get_help_unknown_doctype(self):
		"""Test getting help for unknown DocType."""
		from advanced_compliance.advanced_compliance.help import get_help

		help_data = get_help("Unknown DocType")

		self.assertIn("title", help_data)
		self.assertIn("description", help_data)

	def test_get_all_help_topics(self):
		"""Test getting all help topics."""
		from advanced_compliance.advanced_compliance.help import get_all_help_topics

		topics = get_all_help_topics()

		self.assertIsInstance(topics, list)
		self.assertTrue(len(topics) > 0)

		for topic in topics:
			self.assertIn("doctype", topic)
			self.assertIn("title", topic)

	def test_get_quick_start_guide(self):
		"""Test getting quick start guide."""
		from advanced_compliance.advanced_compliance.help import get_quick_start_guide

		guide = get_quick_start_guide()

		self.assertIn("title", guide)
		self.assertIn("steps", guide)
		self.assertTrue(len(guide["steps"]) > 0)

		for step in guide["steps"]:
			self.assertIn("number", step)
			self.assertIn("title", step)
			self.assertIn("description", step)


class TestDemoDataGenerator(unittest.TestCase):
	"""Tests for demo data generation."""

	@classmethod
	def setUpClass(cls):
		"""Set up test data once."""
		frappe.set_user("Administrator")

	def setUp(self):
		"""Set up before each test."""
		frappe.db.rollback()

	def tearDown(self):
		"""Clean up after each test."""
		frappe.db.rollback()

	def test_generate_demo_data(self):
		"""Test demo data generation (finance & accounting)."""
		from advanced_compliance.advanced_compliance.demo.finance_accounting_data import (
			setup_finance_accounting_data,
		)

		result = setup_finance_accounting_data()

		self.assertIn("controls", result)
		self.assertIn("risks", result)
		self.assertGreater(result["controls"], 0)
		self.assertGreater(result["risks"], 0)

	def test_clear_demo_data(self):
		"""Test demo data clearing (finance & accounting)."""
		from advanced_compliance.advanced_compliance.demo.finance_accounting_data import (
			clear_finance_accounting_data,
			setup_finance_accounting_data,
		)

		# First generate some data
		setup_finance_accounting_data()

		# Then clear it
		result = clear_finance_accounting_data()

		self.assertIn("controls", result)


class TestTranslations(unittest.TestCase):
	"""Tests for translation files."""

	def test_translation_files_exist(self):
		"""Test that translation files exist."""
		import os

		translations_dir = frappe.get_app_path("advanced_compliance", "translations")

		expected_files = ["de.csv", "es.csv", "fr.csv"]

		for filename in expected_files:
			filepath = os.path.join(translations_dir, filename)
			self.assertTrue(os.path.exists(filepath), f"Translation file {filename} does not exist")

	def test_translation_file_format(self):
		"""Test that translation files have correct format."""
		import csv
		import os

		translations_dir = frappe.get_app_path("advanced_compliance", "translations")

		for filename in ["de.csv", "es.csv", "fr.csv"]:
			filepath = os.path.join(translations_dir, filename)

			if os.path.exists(filepath):
				with open(filepath, encoding="utf-8") as f:
					reader = csv.reader(f)
					header = next(reader)

					# Check header format
					self.assertEqual(header[0], "source")
					self.assertEqual(header[1], "translated")

					# Check that file has content
					row_count = sum(1 for _ in reader)
					self.assertGreater(row_count, 0)
