# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Alert Manager

Manages notifications for regulatory changes including
system notifications, email alerts, and weekly digests.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate


class RegulatoryAlertManager:
	"""
	Manage notifications for regulatory changes.

	Sends system notifications, email alerts, and periodic digests
	to compliance stakeholders.
	"""

	# Roles that should receive regulatory notifications
	COMPLIANCE_ROLES = ["Compliance Admin", "Compliance Officer", "Internal Auditor"]

	def __init__(self):
		"""Initialize alert manager."""
		self.settings = self._get_settings()

	def _get_settings(self):
		"""Get notification settings."""
		try:
			return frappe.get_single("Compliance Settings")
		except Exception:
			return frappe._dict()

	def notify_new_update(self, regulatory_update):
		"""
		Notify stakeholders of new regulatory update.

		Args:
			regulatory_update: Regulatory Update document name or doc
		"""
		if isinstance(regulatory_update, str):
			# Validate document exists
			if not frappe.db.exists("Regulatory Update", regulatory_update):
				frappe.log_error(
					message=f"Regulatory Update {regulatory_update} does not exist",
					title="Alert Notification Skipped",
				)
				return

			update = frappe.get_doc("Regulatory Update", regulatory_update)
		else:
			update = regulatory_update

		# Create system notification
		self._create_notification(
			subject=_("New Regulatory Update: {0}").format(update.title[:50]),
			message=_("A new regulatory update has been ingested from {0}. " "Document type: {1}").format(
				update.regulatory_body or "External Source", update.document_type or "Unknown"
			),
			for_roles=self.COMPLIANCE_ROLES,
			document_type="Regulatory Update",
			document_name=update.name,
		)

		# Send email for high-priority updates
		if update.document_type in ("Rule", "Amendment", "Enforcement"):
			self._send_email_alert(
				subject=_("Important Regulatory Update: {0}").format(update.title[:80]),
				message=self._format_update_email(update),
				for_roles=self.COMPLIANCE_ROLES,
			)

	def notify_impact_assessment(self, impact_assessment):
		"""
		Notify control owner of impact assessment.

		Args:
			impact_assessment: Regulatory Impact Assessment document name
		"""
		if isinstance(impact_assessment, str):
			# Validate document exists
			if not frappe.db.exists("Regulatory Impact Assessment", impact_assessment):
				frappe.log_error(
					message=f"Regulatory Impact Assessment {impact_assessment} does not exist",
					title="Alert Notification Skipped",
				)
				return

			assessment = frappe.get_doc("Regulatory Impact Assessment", impact_assessment)
		else:
			assessment = impact_assessment

		# Validate control exists before loading
		if not frappe.db.exists("Control Activity", assessment.control_activity):
			frappe.log_error(
				message=f"Control Activity {assessment.control_activity} does not exist for assessment {assessment.name}",
				title="Alert Notification Skipped",
			)
			return

		control = frappe.get_doc("Control Activity", assessment.control_activity)

		# Notify control owner
		if control.control_owner:
			control_name = control.control_name or control.name

			self._create_notification(
				subject=_("Regulatory Impact on Your Control: {0}").format(control_name[:50]),
				message=_(
					"A regulatory change may affect control '{0}'. "
					"Impact type: {1}. Please review the assessment."
				).format(control_name, assessment.impact_type or "Review Required"),
				for_user=control.control_owner,
				document_type="Regulatory Impact Assessment",
				document_name=assessment.name,
			)

	def notify_upcoming_effective_date(self, days_ahead=30):
		"""
		Notify of upcoming regulatory effective dates.

		Args:
			days_ahead: Days ahead to check for deadlines
		"""
		upcoming_date = add_days(nowdate(), days_ahead)
		today = getdate(nowdate())

		updates = frappe.get_all(
			"Regulatory Update",
			filters={
				"effective_date": ["<=", upcoming_date],
				"effective_date": [">=", today],
				"status": ["not in", ["Implemented", "Not Applicable"]],
			},
			fields=["name", "title", "effective_date", "document_type"],
		)

		for update in updates:
			days_until = (getdate(update.effective_date) - today).days

			urgency = "Critical" if days_until <= 7 else ("High" if days_until <= 14 else "Medium")

			self._create_notification(
				subject=_("Upcoming Deadline: {0} ({1} days)").format(update.title[:40], days_until),
				message=_("Regulatory update '{0}' becomes effective on {1}. " "{2} days remaining.").format(
					update.title, frappe.format(update.effective_date, "Date"), days_until
				),
				for_roles=self.COMPLIANCE_ROLES,
				document_type="Regulatory Update",
				document_name=update.name,
			)

			# Email for critical deadlines
			if urgency == "Critical":
				self._send_email_alert(
					subject=_("URGENT: Regulatory Deadline in {0} days - {1}").format(
						days_until, update.title[:60]
					),
					message=_(
						"The regulatory update '{0}' becomes effective on {1}.\n\n"
						"Only {2} days remaining to ensure compliance.\n\n"
						"Document Type: {3}\n\n"
						"Please review and take necessary action immediately."
					).format(
						update.title,
						frappe.format(update.effective_date, "Date"),
						days_until,
						update.document_type or "Unknown",
					),
					for_roles=self.COMPLIANCE_ROLES,
				)

	def send_weekly_digest(self):
		"""Send weekly regulatory digest email."""
		week_ago = add_days(nowdate(), -7)

		# Get new updates from past week
		new_updates = frappe.get_all(
			"Regulatory Update",
			filters={"creation": [">=", week_ago]},
			fields=["name", "title", "regulatory_body", "publication_date", "document_type"],
			order_by="publication_date desc",
			limit=20,
		)

		# Get pending impact assessments
		pending_assessments = frappe.get_all(
			"Regulatory Impact Assessment",
			filters={"status": "Pending"},
			fields=["name", "control_activity", "impact_type", "priority", "confidence_score"],
			order_by="priority desc",
			limit=20,
		)

		# Get upcoming deadlines
		upcoming = frappe.get_all(
			"Regulatory Update",
			filters={
				"effective_date": ["<=", add_days(nowdate(), 30)],
				"effective_date": [">=", nowdate()],
				"status": ["not in", ["Implemented", "Not Applicable"]],
			},
			fields=["name", "title", "effective_date"],
			order_by="effective_date asc",
			limit=10,
		)

		# Don't send if nothing to report
		if not new_updates and not pending_assessments and not upcoming:
			return

		# Format digest content
		content = self._format_weekly_digest(new_updates, pending_assessments, upcoming, week_ago)

		self._send_email_alert(
			subject=_("Weekly Regulatory Digest - {0}").format(frappe.format(nowdate(), "Date")),
			message=content,
			for_roles=self.COMPLIANCE_ROLES,
		)

	def _create_notification(
		self, subject, message, for_user=None, for_roles=None, document_type=None, document_name=None
	):
		"""
		Create system notification.

		Args:
			subject: Notification subject
			message: Notification message
			for_user: Specific user (optional)
			for_roles: List of roles (optional)
			document_type: Link to DocType (optional)
			document_name: Link to document (optional)
		"""
		users = []

		if for_user:
			users.append(for_user)
		elif for_roles:
			for role in for_roles:
				role_users = frappe.get_all(
					"Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"
				)
				users.extend(role_users)

		# Deduplicate and filter
		users = list(set(users))

		for user in users:
			# Skip if user doesn't exist or is disabled
			user_doc = frappe.db.get_value("User", user, ["enabled", "user_type"], as_dict=True)

			if not user_doc or not user_doc.enabled:
				continue

			if user_doc.user_type == "Website User":
				continue

			try:
				notification = frappe.get_doc(
					{
						"doctype": "Notification Log",
						"subject": subject,
						"email_content": message,
						"for_user": user,
						"document_type": document_type,
						"document_name": document_name,
						"type": "Alert",
					}
				)
				notification.insert(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(
					message=f"Error creating notification for {user}: {str(e)}",
					title=_("Notification Creation Error"),
				)

		frappe.db.commit()

	def _send_email_alert(self, subject, message, for_user=None, for_roles=None):
		"""
		Send email alert.

		Args:
			subject: Email subject
			message: Email content
			for_user: Specific user (optional)
			for_roles: List of roles (optional)
		"""
		recipients = []

		if for_user:
			user_email = frappe.db.get_value("User", for_user, "email")
			if user_email:
				recipients.append(user_email)
		elif for_roles:
			for role in for_roles:
				users = frappe.get_all(
					"Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"
				)
				for user_name in users:
					user = frappe.db.get_value(
						"User", user_name, ["email", "enabled", "user_type"], as_dict=True
					)
					if user and user.enabled and user.user_type != "Website User" and user.email:
						recipients.append(user.email)

		recipients = list(set(recipients))

		if recipients:
			try:
				frappe.sendmail(
					recipients=recipients,
					subject=subject,
					message=message,
					now=False,  # Queue for sending
				)
			except Exception as e:
				frappe.log_error(message=f"Error sending email: {str(e)}", title=_("Email Send Error"))

	def _format_update_email(self, update):
		"""
		Format email content for regulatory update.

		Args:
			update: Regulatory Update document

		Returns:
			str: Formatted email content
		"""
		lines = [
			_("A new regulatory update requires your attention."),
			"",
			_("Title: {0}").format(update.title),
			_("Source: {0}").format(update.regulatory_body or "External"),
			_("Document Type: {0}").format(update.document_type or "Unknown"),
		]

		if update.publication_date:
			lines.append(_("Publication Date: {0}").format(frappe.format(update.publication_date, "Date")))

		if update.effective_date:
			lines.append(_("Effective Date: {0}").format(frappe.format(update.effective_date, "Date")))

		if update.summary:
			lines.extend(["", _("Summary:"), update.summary[:500]])

		if update.original_url:
			lines.extend(["", _("Original Source: {0}").format(update.original_url)])

		lines.extend(["", _("Please review this update in the system.")])

		return "\n".join(lines)

	def _format_weekly_digest(self, updates, assessments, upcoming, week_start):
		"""
		Format weekly digest email content.

		Args:
			updates: List of new updates
			assessments: List of pending assessments
			upcoming: List of upcoming deadlines
			week_start: Start of reporting week

		Returns:
			str: Formatted digest content
		"""
		lines = [
			_("Weekly Regulatory Digest"),
			_("Period: {0} to {1}").format(
				frappe.format(week_start, "Date"), frappe.format(nowdate(), "Date")
			),
			"=" * 50,
			"",
		]

		# New updates section
		if updates:
			lines.extend([_("NEW REGULATORY UPDATES ({0})").format(len(updates)), "-" * 30])
			for update in updates:
				lines.append(f"• {update.title[:60]} ({update.regulatory_body or 'Unknown'})")
			lines.append("")

		# Pending assessments section
		if assessments:
			lines.extend([_("PENDING IMPACT ASSESSMENTS ({0})").format(len(assessments)), "-" * 30])
			for assessment in assessments:
				control_name = (
					frappe.db.get_value("Control Activity", assessment.control_activity, "control_name")
					or assessment.control_activity
				)
				lines.append(
					f"• {control_name[:40]} - {assessment.impact_type} "
					f"(Confidence: {assessment.confidence_score:.0f}%)"
				)
			lines.append("")

		# Upcoming deadlines section
		if upcoming:
			lines.extend([_("UPCOMING REGULATORY DEADLINES"), "-" * 30])
			for item in upcoming:
				days = (getdate(item.effective_date) - getdate(nowdate())).days
				lines.append(
					f"• {item.title[:50]} - {frappe.format(item.effective_date, 'Date')} " f"({days} days)"
				)
			lines.append("")

		# Footer
		lines.extend(
			[
				"=" * 50,
				_(
					"This is an automated digest. Please review the compliance portal "
					"for detailed information."
				),
			]
		)

		return "\n".join(lines)
