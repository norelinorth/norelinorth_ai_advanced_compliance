"""
Test suite for Risk Register Entry DocType.

Coverage:
- Basic CRUD operations
- Risk score calculations
- Risk level determination
- Status management
- Control linkage
"""

import unittest

import frappe
from frappe.utils import nowdate


class TestRiskRegisterEntry(unittest.TestCase):
	"""Test cases for Risk Register Entry DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

		# Ensure Compliance Settings has medium_risk_threshold configured
		settings = frappe.get_single("Compliance Settings")
		if not settings.get("medium_risk_threshold"):
			settings.medium_risk_threshold = 6
			settings.save(ignore_permissions=True)
			frappe.db.commit()

	def setUp(self):
		"""Set up before each test."""
		frappe.db.rollback()

	def tearDown(self):
		"""Clean up after each test."""
		frappe.db.rollback()

	def test_01_create_risk_entry(self):
		"""Test basic risk entry creation."""
		risk = create_test_risk()
		self.assertTrue(risk.name)
		self.assertEqual(risk.status, "Open")
		self.assertEqual(risk.risk_name, "Test Risk Entry")

	def test_02_inherent_risk_score_calculation(self):
		"""Test inherent risk score calculation."""
		risk = frappe.get_doc(
			{
				"doctype": "Risk Register Entry",
				"risk_name": "Inherent Score Test",
				"inherent_likelihood": "4 - Likely",
				"inherent_impact": "3 - High",
			}
		)
		risk.insert()

		# 4 * 3 = 12
		self.assertEqual(risk.inherent_risk_score, 12)

	def test_03_residual_risk_score_calculation(self):
		"""Test residual risk score calculation."""
		risk = frappe.get_doc(
			{
				"doctype": "Risk Register Entry",
				"risk_name": "Residual Score Test",
				"residual_likelihood": "2 - Unlikely",
				"residual_impact": "2 - Medium",
			}
		)
		risk.insert()

		# 2 * 2 = 4
		self.assertEqual(risk.residual_risk_score, 4)

	def test_04_both_scores_calculation(self):
		"""Test calculation of both inherent and residual scores."""
		risk = frappe.get_doc(
			{
				"doctype": "Risk Register Entry",
				"risk_name": "Both Scores Test",
				"inherent_likelihood": "5 - Almost Certain",
				"inherent_impact": "4 - Critical",
				"residual_likelihood": "3 - Possible",
				"residual_impact": "2 - Medium",
			}
		)
		risk.insert()

		# Inherent: 5 * 4 = 20
		self.assertEqual(risk.inherent_risk_score, 20)
		# Residual: 3 * 2 = 6
		self.assertEqual(risk.residual_risk_score, 6)

	def test_05_risk_level_critical(self):
		"""Test critical risk level determination."""
		risk = frappe.get_doc(
			{
				"doctype": "Risk Register Entry",
				"risk_name": "Critical Risk Test",
				"residual_likelihood": "4 - Likely",
				"residual_impact": "4 - Critical",  # Score 16
			}
		)
		risk.insert()

		level = risk.get_risk_level()
		self.assertEqual(level, "Critical")

	def test_06_risk_level_high(self):
		"""Test high risk level determination."""
		risk = frappe.get_doc(
			{
				"doctype": "Risk Register Entry",
				"risk_name": "High Risk Test",
				"residual_likelihood": "4 - Likely",
				"residual_impact": "3 - High",  # Score 12
			}
		)
		risk.insert()

		level = risk.get_risk_level()
		self.assertEqual(level, "High")

	def test_07_risk_level_medium(self):
		"""Test medium risk level determination."""
		risk = frappe.get_doc(
			{
				"doctype": "Risk Register Entry",
				"risk_name": "Medium Risk Test",
				"residual_likelihood": "3 - Possible",
				"residual_impact": "2 - Medium",  # Score 6
			}
		)
		risk.insert()

		level = risk.get_risk_level()
		self.assertEqual(level, "Medium")

	def test_08_risk_level_low(self):
		"""Test low risk level determination."""
		risk = frappe.get_doc(
			{
				"doctype": "Risk Register Entry",
				"risk_name": "Low Risk Test",
				"residual_likelihood": "1 - Rare",
				"residual_impact": "1 - Low",  # Score 1
			}
		)
		risk.insert()

		level = risk.get_risk_level()
		self.assertEqual(level, "Low")

	def test_09_risk_level_unknown(self):
		"""Test unknown risk level when no score."""
		risk = create_test_risk()

		level = risk.get_risk_level()
		self.assertEqual(level, "Unknown")

	def test_10_status_transitions(self):
		"""Test valid status transitions."""
		risk = create_test_risk()

		# Open -> Mitigated
		risk.status = "Mitigated"
		risk.save()
		self.assertEqual(risk.status, "Mitigated")

		# Mitigated -> Accepted
		risk.status = "Accepted"
		risk.save()
		self.assertEqual(risk.status, "Accepted")

		# Accepted -> Closed
		risk.status = "Closed"
		risk.save()
		self.assertEqual(risk.status, "Closed")

	def test_11_transferred_status(self):
		"""Test transferred status."""
		risk = create_test_risk()

		risk.status = "Transferred"
		risk.save()
		self.assertEqual(risk.status, "Transferred")

	def test_12_risk_category_link(self):
		"""Test risk category linking."""
		categories = frappe.get_all("Risk Category", limit=1)
		if not categories:
			self.skipTest("No Risk Categories available")

		risk = frappe.get_doc(
			{
				"doctype": "Risk Register Entry",
				"risk_name": "Categorized Risk",
				"risk_category": categories[0].name,
			}
		)
		risk.insert()

		self.assertEqual(risk.risk_category, categories[0].name)

	def test_13_score_update_on_save(self):
		"""Test that scores update correctly on save."""
		risk = create_test_risk()

		# Initially no scores (None or 0)
		self.assertIn(risk.inherent_risk_score, [None, 0])
		self.assertIn(risk.residual_risk_score, [None, 0])

		# Update values
		risk.inherent_likelihood = "3 - Possible"
		risk.inherent_impact = "3 - High"
		risk.save()

		# Score should update
		self.assertEqual(risk.inherent_risk_score, 9)


def create_test_risk(risk_name="Test Risk Entry"):
	"""Helper function to create a test risk entry."""
	risk = frappe.get_doc({"doctype": "Risk Register Entry", "risk_name": risk_name, "status": "Open"})
	risk.insert()
	return risk
