# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
API Endpoints for Regulatory Feeds

Provides whitelisted API methods for regulatory feed operations.
"""

import frappe
from frappe import _


@frappe.whitelist()
def sync_feed(feed_source):
	"""
	Manually trigger sync for a feed source.

	Args:
		feed_source: Regulatory Feed Source name

	Returns:
		dict: Sync results with count of new updates
	"""
	if not frappe.has_permission("Regulatory Feed Source", "write"):
		frappe.throw(
			_("Insufficient permissions to sync feeds. Requires write permission on Regulatory Feed Source.")
		)

	# Validate feed source exists
	if not frappe.db.exists("Regulatory Feed Source", feed_source):
		frappe.throw(_("Regulatory Feed Source {0} does not exist").format(frappe.bold(feed_source)))

	from .connectors import get_connector

	feed_doc = frappe.get_doc("Regulatory Feed Source", feed_source)
	connector = get_connector(feed_doc)

	count = connector.sync()

	return {"success": True, "updates_count": count, "message": _("{0} new updates synced").format(count)}


@frappe.whitelist()
def sync_all_feeds():
	"""
	Sync all enabled feed sources.

	Returns:
		dict: Sync results
	"""
	if not frappe.has_permission("Regulatory Feed Source", "write"):
		frappe.throw(
			_("Insufficient permissions to sync feeds. Requires write permission on Regulatory Feed Source.")
		)

	from .scheduler import sync_all_feeds as do_sync

	# Run in background for large syncs
	frappe.enqueue(do_sync, queue="long", timeout=600)

	return {"success": True, "message": _("Feed sync started in background")}


@frappe.whitelist()
def analyze_update_impact(regulatory_update):
	"""
	Analyze impact of a regulatory update.

	Args:
		regulatory_update: Regulatory Update name

	Returns:
		dict: Analysis results with created assessments
	"""
	if not frappe.has_permission("Regulatory Impact Assessment", "create"):
		frappe.throw(
			_(
				"Insufficient permissions to create impact assessments. Requires create permission on Regulatory Impact Assessment."
			)
		)

	from .mapping.impact_mapper import ImpactMapper

	# Get all changes for this update
	changes = frappe.get_all(
		"Regulatory Change", filters={"regulatory_update": regulatory_update}, pluck="name"
	)

	all_assessments = []

	for change_name in changes:
		# Skip if change was deleted
		if not frappe.db.exists("Regulatory Change", change_name):
			continue

		change_doc = frappe.get_doc("Regulatory Change", change_name)
		mapper = ImpactMapper(change_doc)
		assessments = mapper.create_impact_assessments()
		all_assessments.extend(assessments)

	return {"success": True, "assessments_created": len(all_assessments), "assessment_names": all_assessments}


@frappe.whitelist()
def extract_update_metadata(regulatory_update):
	"""
	Extract metadata from regulatory update text.

	Args:
		regulatory_update: Regulatory Update name

	Returns:
		dict: Extracted metadata
	"""
	if not frappe.has_permission("Regulatory Update", "write"):
		frappe.throw(
			_("Insufficient permissions to extract metadata. Requires write permission on Regulatory Update.")
		)

	# Validate update exists
	if not frappe.db.exists("Regulatory Update", regulatory_update):
		frappe.throw(_("Regulatory Update {0} does not exist").format(frappe.bold(regulatory_update)))

	update_doc = frappe.get_doc("Regulatory Update", regulatory_update)
	update_doc.extract_metadata()

	return {
		"success": True,
		"citations": update_doc.citations,
		"keywords": update_doc.extracted_keywords,
		"entities": update_doc.extracted_entities,
		"effective_date": update_doc.effective_date,
	}


@frappe.whitelist()
def get_regulatory_timeline(days=90):
	"""
	Get upcoming regulatory effective dates.

	Args:
		days: Days ahead to look (default: 90)

	Returns:
		list: Upcoming regulatory deadlines
	"""
	if not frappe.has_permission("Regulatory Update", "read"):
		frappe.throw(
			_(
				"Insufficient permissions to view regulatory timeline. Requires read permission on Regulatory Update."
			)
		)

	from frappe.utils import add_days, cint, nowdate

	future_date = add_days(nowdate(), cint(days))

	updates = frappe.get_all(
		"Regulatory Update",
		filters={
			"effective_date": ["between", [nowdate(), future_date]],
			"status": ["not in", ["Implemented", "Not Applicable"]],
		},
		fields=[
			"name",
			"title",
			"regulatory_body",
			"effective_date",
			"document_type",
			"status",
			"days_until_effective",
		],
		order_by="effective_date asc",
	)

	return updates


@frappe.whitelist()
def get_pending_actions(user=None):
	"""
	Get pending regulatory actions for user.

	Args:
		user: User to filter by (default: current user)

	Returns:
		list: Pending action items
	"""
	user = user or frappe.session.user

	# Security: Only allow viewing own pending actions unless user is System Manager
	if user != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(
			_(
				"You can only view your own pending actions. System Manager role required to view other users' actions."
			)
		)

	assessments = frappe.get_all(
		"Regulatory Impact Assessment",
		filters={"assigned_to": user, "status": ["in", ["Pending", "In Progress"]]},
		fields=[
			"name",
			"control_activity",
			"impact_type",
			"due_date",
			"status",
			"gap_identified",
			"priority",
			"confidence_score",
		],
		order_by="priority desc, due_date asc",
	)

	# Enrich with control names - bulk fetch to avoid N+1 queries
	if assessments:
		control_ids = [a["control_activity"] for a in assessments if a.get("control_activity")]
		if control_ids:
			controls = frappe.get_all(
				"Control Activity", filters={"name": ["in", control_ids]}, fields=["name", "control_name"]
			)
			control_map = {c.name: c.control_name for c in controls}
			for assessment in assessments:
				assessment["control_name"] = control_map.get(assessment.get("control_activity"))

	return assessments


@frappe.whitelist()
def get_feed_status():
	"""
	Get status of all regulatory feeds.

	Returns:
		list: Feed status information
	"""
	if not frappe.has_permission("Regulatory Feed Source", "read"):
		frappe.throw(
			_(
				"Insufficient permissions to view feed status. Requires read permission on Regulatory Feed Source."
			)
		)

	feeds = frappe.get_all(
		"Regulatory Feed Source",
		fields=[
			"name",
			"source_name",
			"feed_type",
			"enabled",
			"last_sync",
			"last_sync_status",
			"sync_frequency",
			"regulatory_body",
		],
	)

	for feed in feeds:
		# Get update count
		feed["update_count"] = frappe.db.count("Regulatory Update", filters={"source": feed["name"]})

		# Calculate sync status
		if not feed["last_sync"]:
			feed["health"] = "warning"
			feed["health_message"] = _("Never synced")
		elif feed["last_sync_status"] == "Failed":
			feed["health"] = "danger"
			feed["health_message"] = _("Last sync failed")
		else:
			from frappe.utils import now_datetime, time_diff_in_hours

			hours_since = time_diff_in_hours(now_datetime(), feed["last_sync"])

			if feed["sync_frequency"] == "Hourly" and hours_since > 2:
				feed["health"] = "warning"
				feed["health_message"] = _("Sync overdue")
			elif feed["sync_frequency"] == "Daily" and hours_since > 26:
				feed["health"] = "warning"
				feed["health_message"] = _("Sync overdue")
			else:
				feed["health"] = "success"
				feed["health_message"] = _("OK")

	return feeds


@frappe.whitelist()
def get_compliance_dashboard_data():
	"""
	Get dashboard data for regulatory compliance overview.

	Returns:
		dict: Dashboard statistics and data
	"""
	if not frappe.has_permission("Regulatory Update", "read"):
		frappe.throw(
			_(
				"Insufficient permissions to view compliance dashboard. Requires read permission on Regulatory Update."
			)
		)

	from frappe.utils import add_days, nowdate

	# Count by status (using frappe.db.sql for v15/v16 compatibility)
	updates_by_status = frappe.db.sql(
		"""
		SELECT status, COUNT(*) as count
		FROM `tabRegulatory Update`
		GROUP BY status
		""",
		as_dict=True,
	)

	# Pending assessments
	pending_assessments = frappe.db.count(
		"Regulatory Impact Assessment", filters={"status": ["in", ["Pending", "In Progress"]]}
	)

	# Upcoming deadlines (30 days)
	upcoming_deadline_count = frappe.db.count(
		"Regulatory Update",
		filters={
			"effective_date": ["between", [nowdate(), add_days(nowdate(), 30)]],
			"status": ["not in", ["Implemented", "Not Applicable"]],
		},
	)

	# Recent updates (7 days)
	recent_updates = frappe.get_all(
		"Regulatory Update",
		filters={"creation": [">=", add_days(nowdate(), -7)]},
		fields=["name", "title", "regulatory_body", "document_type", "creation"],
		order_by="creation desc",
		limit=5,
	)

	# Changes by severity (using frappe.db.sql for v15/v16 compatibility)
	changes_by_severity = frappe.db.sql(
		"""
		SELECT severity, COUNT(*) as count
		FROM `tabRegulatory Change`
		GROUP BY severity
		""",
		as_dict=True,
	)

	return {
		"updates_by_status": {item["status"]: item["count"] for item in updates_by_status},
		"pending_assessments": pending_assessments,
		"upcoming_deadlines": upcoming_deadline_count,
		"recent_updates": recent_updates,
		"changes_by_severity": {item["severity"]: item["count"] for item in changes_by_severity},
	}


@frappe.whitelist()
def mark_assessment_complete(assessment_name, action_taken, notes=None):
	"""
	Mark an impact assessment as complete.

	Args:
		assessment_name: Regulatory Impact Assessment name
		action_taken: Description of action taken
		notes: Optional completion notes

	Returns:
		dict: Success status
	"""
	if not frappe.has_permission("Regulatory Impact Assessment", "write"):
		frappe.throw(
			_(
				"Insufficient permissions to complete assessment. Requires write permission on Regulatory Impact Assessment."
			)
		)

	# Validate assessment exists
	if not frappe.db.exists("Regulatory Impact Assessment", assessment_name):
		frappe.throw(
			_("Regulatory Impact Assessment {0} does not exist").format(frappe.bold(assessment_name))
		)

	assessment = frappe.get_doc("Regulatory Impact Assessment", assessment_name)
	assessment.mark_complete(action_taken, notes)

	return {"success": True, "message": _("Assessment marked complete")}


@frappe.whitelist()
def mark_assessment_no_action(assessment_name, reason):
	"""
	Mark that no action is needed for an assessment.

	Args:
		assessment_name: Regulatory Impact Assessment name
		reason: Explanation why no action is needed

	Returns:
		dict: Success status
	"""
	if not frappe.has_permission("Regulatory Impact Assessment", "write"):
		frappe.throw(
			_(
				"Insufficient permissions to mark assessment. Requires write permission on Regulatory Impact Assessment."
			)
		)

	# Validate assessment exists
	if not frappe.db.exists("Regulatory Impact Assessment", assessment_name):
		frappe.throw(
			_("Regulatory Impact Assessment {0} does not exist").format(frappe.bold(assessment_name))
		)

	assessment = frappe.get_doc("Regulatory Impact Assessment", assessment_name)
	assessment.mark_no_action(reason)

	return {"success": True, "message": _("Assessment marked as no action needed")}
