"""
Test suite for Control Activity DocType.

Coverage:
- Basic CRUD operations
- Validation rules
- Key control requirements
- COSO mapping validation
- Next test date calculation
- Status transitions
"""

import unittest

import frappe
from frappe.utils import add_months, getdate, nowdate


class TestControlActivity(unittest.TestCase):
	"""Test cases for Control Activity DocType."""

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

	def test_01_create_control_activity(self):
		"""Test basic control activity creation."""
		control = create_test_control()
		self.assertTrue(control.name)
		self.assertEqual(control.status, "Draft")
		self.assertEqual(control.control_name, "Test Control Activity")

	def test_02_key_control_requires_test_frequency(self):
		"""Test that key controls require test frequency."""
		control = frappe.get_doc(
			{
				"doctype": "Control Activity",
				"control_name": "Key Control Without Frequency",
				"control_owner": "Administrator",
				"is_key_control": 1,
			}
		)

		with self.assertRaises(frappe.ValidationError):
			control.insert()

	def test_03_key_control_with_frequency(self):
		"""Test that key controls with frequency pass validation."""
		control = frappe.get_doc(
			{
				"doctype": "Control Activity",
				"control_name": "Key Control With Frequency",
				"control_owner": "Administrator",
				"is_key_control": 1,
				"test_frequency": "Quarterly",
			}
		)
		control.insert()
		self.assertTrue(control.name)
		self.assertEqual(control.is_key_control, 1)

	def test_04_coso_component_principle_mismatch(self):
		"""Test COSO component and principle validation."""
		# Get a principle from Control Environment
		principles = frappe.get_all("COSO Principle", filters={"component": "Control Environment"}, limit=1)

		if not principles:
			self.skipTest("No COSO Principles available")

		# Try to create control with mismatched component
		control = frappe.get_doc(
			{
				"doctype": "Control Activity",
				"control_name": "Mismatched COSO Control",
				"control_owner": "Administrator",
				"coso_component": "Risk Assessment",  # Wrong component
				"coso_principle": principles[0].name,
			}
		)

		with self.assertRaises(frappe.ValidationError):
			control.insert()

	def test_05_next_test_date_calculation(self):
		"""Test next test date calculation based on frequency."""
		control = frappe.get_doc(
			{
				"doctype": "Control Activity",
				"control_name": "Test Date Calculation Control",
				"control_owner": "Administrator",
				"test_frequency": "Quarterly",
				"last_test_date": nowdate(),
			}
		)
		control.insert()

		expected_next_date = add_months(getdate(nowdate()), 3)
		self.assertEqual(getdate(control.next_test_date), expected_next_date)

	def test_06_monthly_test_frequency(self):
		"""Test monthly test frequency calculation."""
		control = frappe.get_doc(
			{
				"doctype": "Control Activity",
				"control_name": "Monthly Test Control",
				"control_owner": "Administrator",
				"test_frequency": "Monthly",
				"last_test_date": nowdate(),
			}
		)
		control.insert()

		expected_next_date = add_months(getdate(nowdate()), 1)
		self.assertEqual(getdate(control.next_test_date), expected_next_date)

	def test_07_annual_test_frequency(self):
		"""Test annual test frequency calculation."""
		control = frappe.get_doc(
			{
				"doctype": "Control Activity",
				"control_name": "Annual Test Control",
				"control_owner": "Administrator",
				"test_frequency": "Annually",
				"last_test_date": nowdate(),
			}
		)
		control.insert()

		expected_next_date = add_months(getdate(nowdate()), 12)
		self.assertEqual(getdate(control.next_test_date), expected_next_date)

	def test_08_status_transitions(self):
		"""Test valid status transitions."""
		control = create_test_control()

		# Draft -> Active
		control.status = "Active"
		control.save()
		self.assertEqual(control.status, "Active")

		# Active -> Under Review
		control.status = "Under Review"
		control.save()
		self.assertEqual(control.status, "Under Review")

		# Under Review -> Deprecated
		control.status = "Deprecated"
		control.save()
		self.assertEqual(control.status, "Deprecated")

	def test_09_control_type_values(self):
		"""Test valid control types."""
		valid_types = ["Preventive", "Detective", "Corrective"]

		for control_type in valid_types:
			control = frappe.get_doc(
				{
					"doctype": "Control Activity",
					"control_name": f"{control_type} Control",
					"control_owner": "Administrator",
					"control_type": control_type,
				}
			)
			control.insert()
			self.assertEqual(control.control_type, control_type)
			# Use force=True to handle linked graph entities
			frappe.delete_doc("Control Activity", control.name, force=True)

	def test_10_automation_levels(self):
		"""Test valid automation levels."""
		valid_levels = ["Manual", "Semi-automated", "Fully Automated"]

		for level in valid_levels:
			control = frappe.get_doc(
				{
					"doctype": "Control Activity",
					"control_name": f"{level} Control",
					"control_owner": "Administrator",
					"automation_level": level,
				}
			)
			control.insert()
			self.assertEqual(control.automation_level, level)
			# Use force=True to handle linked graph entities
			frappe.delete_doc("Control Activity", control.name, force=True)

	def test_11_update_test_info(self):
		"""Test update_test_info method."""
		control = create_test_control()
		control.test_frequency = "Quarterly"
		control.save()

		test_date = nowdate()
		control.update_test_info(test_date, "Effective")

		control.reload()
		self.assertEqual(control.last_test_date, getdate(test_date))
		self.assertEqual(control.last_test_result, "Effective")
		self.assertIsNotNone(control.next_test_date)


def create_test_control(control_name="Test Control Activity"):
	"""Helper function to create a test control activity."""
	control = frappe.get_doc(
		{
			"doctype": "Control Activity",
			"control_name": control_name,
			"control_owner": "Administrator",
			"status": "Draft",
		}
	)
	control.insert()
	return control
