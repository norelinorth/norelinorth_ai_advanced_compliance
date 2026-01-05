"""
Test suite for Test Execution DocType.

Coverage:
- Basic CRUD operations
- Submission workflow
- Control update on submit
- Deficiency creation
- Test results validation
"""

import unittest

import frappe
from frappe.utils import getdate, nowdate


class TestTestExecution(unittest.TestCase):
	"""Test cases for Test Execution DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def setUp(self):
		"""Set up before each test."""
		frappe.db.rollback()
		# Create a test control for linking
		self.control = self._create_test_control()

	def tearDown(self):
		"""Clean up after each test."""
		frappe.db.rollback()

	def _create_test_control(self):
		"""Create a control for test execution testing."""
		control = frappe.get_doc(
			{
				"doctype": "Control Activity",
				"control_name": "Control for Test Execution",
				"control_owner": "Administrator",
				"status": "Active",
				"test_frequency": "Quarterly",
			}
		)
		control.insert()
		return control

	def test_01_create_test_execution(self):
		"""Test basic test execution creation."""
		test_exec = frappe.get_doc(
			{
				"doctype": "Test Execution",
				"control": self.control.name,
				"test_date": nowdate(),
				"tester": "Administrator",
			}
		)
		test_exec.insert()

		self.assertTrue(test_exec.name)
		self.assertEqual(test_exec.docstatus, 0)

	def test_02_submit_effective_test(self):
		"""Test submission with effective result."""
		test_exec = frappe.get_doc(
			{
				"doctype": "Test Execution",
				"control": self.control.name,
				"test_date": nowdate(),
				"tester": "Administrator",
				"test_result": "Effective",
				"test_procedure_performed": "Tested control procedures",
				"conclusion": "Control is operating effectively",
			}
		)
		test_exec.insert()
		test_exec.submit()

		self.assertEqual(test_exec.docstatus, 1)

		# Check control was updated
		self.control.reload()
		self.assertEqual(self.control.last_test_result, "Effective")
		self.assertEqual(getdate(self.control.last_test_date), getdate(nowdate()))

	def test_03_submit_ineffective_creates_deficiency(self):
		"""Test that ineffective result creates deficiency."""
		test_exec = frappe.get_doc(
			{
				"doctype": "Test Execution",
				"control": self.control.name,
				"test_date": nowdate(),
				"tester": "Administrator",
				"test_result": "Ineffective - Significant",
				"test_procedure_performed": "Tested control procedures",
				"conclusion": "Control deficiency identified",
			}
		)
		test_exec.insert()
		test_exec.submit()

		# Check deficiency was created
		deficiencies = frappe.get_all("Deficiency", filters={"test_execution": test_exec.name})
		self.assertEqual(len(deficiencies), 1)

	def test_04_submit_minor_ineffective(self):
		"""Test minor ineffective result."""
		test_exec = frappe.get_doc(
			{
				"doctype": "Test Execution",
				"control": self.control.name,
				"test_date": nowdate(),
				"tester": "Administrator",
				"test_result": "Ineffective - Minor",
				"test_procedure_performed": "Tested control procedures",
				"conclusion": "Minor control weakness",
			}
		)
		test_exec.insert()
		test_exec.submit()

		# Check deficiency was created
		deficiencies = frappe.get_all("Deficiency", filters={"test_execution": test_exec.name})
		self.assertEqual(len(deficiencies), 1)

	def test_05_submit_material_ineffective(self):
		"""Test material ineffective result."""
		test_exec = frappe.get_doc(
			{
				"doctype": "Test Execution",
				"control": self.control.name,
				"test_date": nowdate(),
				"tester": "Administrator",
				"test_result": "Ineffective - Material",
				"test_procedure_performed": "Tested control procedures",
				"conclusion": "Material weakness identified",
			}
		)
		test_exec.insert()
		test_exec.submit()

		# Check deficiency severity
		deficiency = frappe.get_doc("Deficiency", {"test_execution": test_exec.name})
		self.assertEqual(deficiency.severity, "Material Weakness")

	def test_06_cancel_test_execution(self):
		"""Test cancellation of test execution."""
		test_exec = frappe.get_doc(
			{
				"doctype": "Test Execution",
				"control": self.control.name,
				"test_date": nowdate(),
				"tester": "Administrator",
				"test_result": "Effective",
				"test_procedure_performed": "Tested",
				"conclusion": "OK",
			}
		)
		test_exec.insert()
		test_exec.submit()
		test_exec.cancel()

		self.assertEqual(test_exec.docstatus, 2)

	def test_07_test_result_options(self):
		"""Test all valid test result options."""
		valid_results = [
			"Effective",
			"Ineffective - Minor",
			"Ineffective - Significant",
			"Ineffective - Material",
			"Not Applicable",
		]

		for i, result in enumerate(valid_results):
			test_exec = frappe.get_doc(
				{
					"doctype": "Test Execution",
					"control": self.control.name,
					"test_date": nowdate(),
					"tester": "Administrator",
					"test_result": result,
					"test_procedure_performed": f"Test {i}",
					"conclusion": f"Conclusion {i}",
				}
			)
			test_exec.insert()
			self.assertEqual(test_exec.test_result, result)

	def test_08_evidence_attachment(self):
		"""Test adding evidence to test execution."""
		test_exec = frappe.get_doc(
			{
				"doctype": "Test Execution",
				"control": self.control.name,
				"test_date": nowdate(),
				"tester": "Administrator",
				"test_evidence": [{"evidence_type": "Screenshot", "description": "Test evidence screenshot"}],
			}
		)
		test_exec.insert()

		self.assertEqual(len(test_exec.test_evidence), 1)
		self.assertEqual(test_exec.test_evidence[0].get("evidence_type"), "Screenshot")


def create_test_execution(control, result="Effective"):
	"""Helper function to create a test execution."""
	test_exec = frappe.get_doc(
		{
			"doctype": "Test Execution",
			"control": control,
			"test_date": nowdate(),
			"tester": "Administrator",
			"test_result": result,
			"test_procedure_performed": "Standard test procedure",
			"conclusion": "Test conclusion",
		}
	)
	test_exec.insert()
	return test_exec
