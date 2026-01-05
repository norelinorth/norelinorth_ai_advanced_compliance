"""
Control Evidence DocType Controller.

Stores captured evidence from ERPNext documents for compliance controls.
"""

import hashlib
import json

import frappe
from frappe import _
from frappe.model.document import Document


class ControlEvidence(Document):
	"""Controller for Control Evidence DocType."""

	def before_insert(self):
		"""Set captured timestamp and generate hash before insert."""
		if not self.captured_at:
			self.captured_at = frappe.utils.now_datetime()

		self.generate_evidence_hash()
		self.generate_summary()

	def generate_evidence_hash(self):
		"""Generate SHA-256 hash for tamper detection."""
		hash_content = json.dumps(
			{
				"source_doctype": self.source_doctype,
				"source_name": self.source_name,
				"captured_at": str(self.captured_at),
				"document_snapshot": self.document_snapshot,
				"workflow_log": self.workflow_log,
				"version_history": self.version_history,
				"comments_log": self.comments_log,
			},
			sort_keys=True,
		)

		self.evidence_hash = f"sha256:{hashlib.sha256(hash_content.encode()).hexdigest()}"

	def generate_summary(self):
		"""Generate human-readable evidence summary."""
		summary_parts = []

		summary_parts.append(_("Evidence captured for {0} {1}").format(self.source_doctype, self.source_name))

		if self.document_snapshot:
			summary_parts.append(_("PDF snapshot captured"))

		if self.workflow_log:
			try:
				workflow_data = json.loads(self.workflow_log)
				summary_parts.append(_("{0} workflow actions recorded").format(len(workflow_data)))
			except (json.JSONDecodeError, TypeError):
				pass

		if self.version_history:
			try:
				version_data = json.loads(self.version_history)
				summary_parts.append(_("{0} versions recorded").format(len(version_data)))
			except (json.JSONDecodeError, TypeError):
				pass

		if self.linked_documents:
			summary_parts.append(_("{0} linked documents captured").format(len(self.linked_documents)))

		self.evidence_summary = "\n".join(summary_parts)

	def verify_integrity(self):
		"""Verify evidence has not been tampered with."""
		original_hash = self.evidence_hash
		self.generate_evidence_hash()
		new_hash = self.evidence_hash

		# Restore original hash
		self.evidence_hash = original_hash

		if original_hash != new_hash:
			frappe.throw(_("Evidence integrity check failed. Evidence may have been tampered with."))

		return True

	@staticmethod
	def get_evidence_for_control(control_activity, from_date=None, to_date=None):
		"""
		Get all evidence for a control activity.

		Args:
		    control_activity: Control Activity name
		    from_date: Optional start date filter
		    to_date: Optional end date filter

		Returns:
		    List of Control Evidence documents
		"""
		filters = {"control_activity": control_activity}

		if from_date:
			filters["captured_at"] = [">=", from_date]
		if to_date:
			if "captured_at" in filters:
				filters["captured_at"] = ["between", [from_date, to_date]]
			else:
				filters["captured_at"] = ["<=", to_date]

		return frappe.get_all(
			"Control Evidence",
			filters=filters,
			fields=[
				"name",
				"source_doctype",
				"source_name",
				"captured_at",
				"document_snapshot",
				"evidence_summary",
			],
			order_by="captured_at desc",
		)
