"""
Test suite for Compliance Settings DocType.

Coverage:
- Settings existence
- Default values
- Threshold configuration
- Feature toggles
"""

import unittest

import frappe


class TestComplianceSettings(unittest.TestCase):
	"""Test cases for Compliance Settings DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def test_01_settings_exists(self):
		"""Test that Compliance Settings exists."""
		settings = frappe.get_single("Compliance Settings")
		self.assertIsNotNone(settings)

	def test_02_enable_compliance_features(self):
		"""Test enable compliance features toggle."""
		settings = frappe.get_single("Compliance Settings")
		self.assertIn(settings.enable_compliance_features, [0, 1])

	def test_03_default_test_frequency(self):
		"""Test default test frequency setting."""
		settings = frappe.get_single("Compliance Settings")

		valid_frequencies = ["Monthly", "Quarterly", "Semi-annually", "Annually"]
		if settings.default_test_frequency:
			self.assertIn(settings.default_test_frequency, valid_frequencies)

	def test_04_risk_score_method(self):
		"""Test risk score method setting."""
		settings = frappe.get_single("Compliance Settings")

		valid_methods = ["Likelihood x Impact", "Weighted Average"]
		if settings.risk_score_method:
			self.assertIn(settings.risk_score_method, valid_methods)

	def test_05_high_risk_threshold(self):
		"""Test high risk threshold configuration."""
		settings = frappe.get_single("Compliance Settings")

		if settings.high_risk_threshold:
			self.assertGreater(settings.high_risk_threshold, 0)
			self.assertLess(settings.high_risk_threshold, 25)

	def test_06_critical_risk_threshold(self):
		"""Test critical risk threshold configuration."""
		settings = frappe.get_single("Compliance Settings")

		if settings.critical_risk_threshold:
			self.assertGreater(settings.critical_risk_threshold, 0)
			self.assertLess(settings.critical_risk_threshold, 25)

	def test_07_threshold_ordering(self):
		"""Test that critical threshold >= high threshold."""
		settings = frappe.get_single("Compliance Settings")

		if settings.high_risk_threshold and settings.critical_risk_threshold:
			self.assertGreaterEqual(settings.critical_risk_threshold, settings.high_risk_threshold)

	def test_08_email_notification_setting(self):
		"""Test email notification toggle."""
		settings = frappe.get_single("Compliance Settings")
		self.assertIn(settings.enable_email_notifications, [0, 1])

	def test_09_days_before_reminder(self):
		"""Test days before test reminder setting."""
		settings = frappe.get_single("Compliance Settings")

		if settings.days_before_test_reminder:
			self.assertGreaterEqual(settings.days_before_test_reminder, 0)
			self.assertLessEqual(settings.days_before_test_reminder, 30)

	def test_10_update_settings(self):
		"""Test updating settings."""
		settings = frappe.get_single("Compliance Settings")

		original_value = settings.days_before_test_reminder
		settings.days_before_test_reminder = 14
		settings.save()

		settings.reload()
		self.assertEqual(settings.days_before_test_reminder, 14)

		# Restore original
		settings.days_before_test_reminder = original_value
		settings.save()
