# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class RegulatoryImpactAssessment(Document):
	"""
	DocType for mapping regulatory changes to affected controls.

	Tracks the impact of regulatory changes on Control Activities
	and the actions required to maintain compliance.
	"""

	def validate(self):
		"""Validate impact assessment."""
		self.set_regulatory_update()
		self.auto_set_priority()

	def before_save(self):
		"""Actions before saving."""
		if self.status == "Control Updated" and not self.completed_date:
			self.completed_date = nowdate()

	def set_regulatory_update(self):
		"""Set regulatory update from regulatory change if not set."""
		if not self.regulatory_update and self.regulatory_change:
			self.regulatory_update = frappe.db.get_value(
				"Regulatory Change", self.regulatory_change, "regulatory_update"
			)

	def auto_set_priority(self):
		"""
		Auto-set priority based on change severity and gap status.
		"""
		if not self.priority and self.regulatory_change:
			severity = frappe.db.get_value("Regulatory Change", self.regulatory_change, "severity")

			# Map severity to priority
			severity_priority_map = {
				"Critical": "Critical",
				"Major": "High",
				"Moderate": "Medium",
				"Minor": "Low",
			}

			self.priority = severity_priority_map.get(severity, "Medium")

			# Upgrade priority if gap identified
			if self.gap_identified and self.priority in ("Medium", "Low"):
				self.priority = "High"

	def assign_to_control_owner(self):
		"""
		Assign this assessment to the control owner.

		Returns:
			str: Assigned user name
		"""
		if not self.control_activity:
			frappe.throw(_("Control Activity is required"))

		control_owner = frappe.db.get_value("Control Activity", self.control_activity, "control_owner")

		if control_owner:
			self.assigned_to = control_owner
			self.save(ignore_permissions=True)

			# Create todo for the owner
			self._create_todo(control_owner)

		return control_owner

	def _create_todo(self, user):
		"""
		Create a ToDo for the assigned user.

		Args:
			user: User to assign ToDo to
		"""
		change_summary = ""
		if self.regulatory_change:
			change_summary = (
				frappe.db.get_value("Regulatory Change", self.regulatory_change, "summary_of_change") or ""
			)

		control_name = ""
		if self.control_activity:
			control_name = (
				frappe.db.get_value("Control Activity", self.control_activity, "control_name")
				or self.control_activity
			)

		frappe.get_doc(
			{
				"doctype": "ToDo",
				"allocated_to": user,
				"reference_type": "Regulatory Impact Assessment",
				"reference_name": self.name,
				"description": _(
					"Review regulatory impact assessment for control '{0}'. " "Change: {1}"
				).format(control_name, change_summary[:200]),
				"priority": self.priority or "Medium",
				"date": self.due_date,
			}
		).insert(ignore_permissions=True)

	def mark_complete(self, action_taken, notes=None):
		"""
		Mark the assessment as complete.

		Args:
			action_taken: Description of action taken
			notes: Optional completion notes

		Returns:
			bool: Success status
		"""
		self.status = "Control Updated"
		self.action_taken = action_taken
		self.completed_date = nowdate()

		if notes:
			self.completion_notes = notes

		self.save(ignore_permissions=True)

		# Close any related ToDos
		frappe.db.set_value(
			"ToDo",
			{"reference_type": "Regulatory Impact Assessment", "reference_name": self.name, "status": "Open"},
			"status",
			"Closed",
		)

		return True

	def mark_no_action(self, reason):
		"""
		Mark that no action is needed.

		Args:
			reason: Explanation why no action is needed

		Returns:
			bool: Success status
		"""
		self.status = "No Action Needed"
		self.completion_notes = reason
		self.completed_date = nowdate()
		self.save(ignore_permissions=True)

		return True

	@staticmethod
	def get_pending_for_user(user=None):
		"""
		Get pending assessments for a user.

		Args:
			user: User to filter by (default: current user)

		Returns:
			list: Pending assessments
		"""
		user = user or frappe.session.user

		return frappe.get_all(
			"Regulatory Impact Assessment",
			filters={"assigned_to": user, "status": ["in", ["Pending", "In Progress"]]},
			fields=["name", "control_activity", "impact_type", "priority", "due_date", "confidence_score"],
			order_by="due_date asc",
		)
