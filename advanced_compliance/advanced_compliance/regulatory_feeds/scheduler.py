# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Scheduler Jobs for Regulatory Feeds

Provides scheduled tasks for:
- Syncing regulatory feeds (hourly/daily)
- Analyzing new updates
- Detecting upcoming deadlines
- Sending weekly digests
"""

import frappe
from frappe import _


def sync_high_priority_feeds():
	"""
	Sync high-priority regulatory feeds (hourly).

	Called by scheduler_events["hourly"].
	Syncs feeds marked with "Hourly" sync frequency.
	"""
	from .connectors import get_connector

	feeds = frappe.get_all(
		"Regulatory Feed Source", filters={"enabled": 1, "sync_frequency": "Hourly"}, pluck="name"
	)

	for feed_name in feeds:
		try:
			feed_doc = frappe.get_doc("Regulatory Feed Source", feed_name)
			connector = get_connector(feed_doc)
			count = connector.sync()

			if count > 0:
				frappe.logger().info(f"Synced {count} updates from {feed_name}")

		except Exception as e:
			frappe.log_error(
				message=f"{str(e)}\n{frappe.get_traceback()}",
				title=_("Feed Sync Error: {0}").format(feed_name),
			)

	frappe.db.commit()


def sync_all_feeds():
	"""
	Sync all enabled regulatory feeds (daily).

	Called by scheduler_events["daily"].
	Syncs all feeds regardless of configured frequency.
	"""
	from .connectors import get_connector

	feeds = frappe.get_all("Regulatory Feed Source", filters={"enabled": 1}, pluck="name")

	total_updates = 0

	for feed_name in feeds:
		try:
			feed_doc = frappe.get_doc("Regulatory Feed Source", feed_name)
			connector = get_connector(feed_doc)
			count = connector.sync()
			total_updates += count

		except Exception as e:
			frappe.log_error(
				message=f"{str(e)}\n{frappe.get_traceback()}",
				title=_("Feed Sync Error: {0}").format(feed_name),
			)

	frappe.db.commit()

	if total_updates > 0:
		frappe.logger().info(f"Daily sync complete: {total_updates} total updates")
		# Trigger analysis of new updates
		analyze_new_updates()


def analyze_new_updates():
	"""
	Analyze impact of new regulatory updates.

	Called after sync_all_feeds or can be run manually.
	Processes updates with status "New".
	"""
	from .mapping.impact_mapper import ImpactMapper
	from .notifications.alert_manager import RegulatoryAlertManager

	alert_manager = RegulatoryAlertManager()

	# Get unanalyzed updates
	updates = frappe.get_all("Regulatory Update", filters={"status": "New"}, pluck="name")

	for update_name in updates:
		try:
			update_doc = frappe.get_doc("Regulatory Update", update_name)

			# Notify of new update
			alert_manager.notify_new_update(update_doc)

			# Extract metadata
			update_doc.extract_metadata()

			# Get or create changes for this update
			changes = frappe.get_all(
				"Regulatory Change", filters={"regulatory_update": update_doc.name}, pluck="name"
			)

			# If no changes exist, create one from the update content
			if not changes and update_doc.full_text:
				change_doc = frappe.get_doc(
					{
						"doctype": "Regulatory Change",
						"regulatory_update": update_doc.name,
						"change_type": "New Requirement",
						"severity": "Moderate",
						"summary_of_change": update_doc.summary or update_doc.title,
						"new_text": update_doc.full_text[:10000],
						"status": "Pending Analysis",
					}
				)
				change_doc.insert(ignore_permissions=True)
				changes = [change_doc.name]

			# Create impact assessments for each change
			for change_name in changes:
				change_doc = frappe.get_doc("Regulatory Change", change_name)
				mapper = ImpactMapper(change_doc)
				assessments = mapper.create_impact_assessments()

				# Notify for each assessment
				for assessment_name in assessments:
					alert_manager.notify_impact_assessment(assessment_name)

			# Update status
			if changes:
				update_doc.status = "Reviewed"
			else:
				update_doc.status = "Pending Review"

			update_doc.save(ignore_permissions=True)

		except Exception as e:
			frappe.log_error(
				message=f"{str(e)}\n{frappe.get_traceback()}",
				title=_("Update Analysis Error: {0}").format(update_name),
			)

	frappe.db.commit()


def detect_upcoming_deadlines():
	"""
	Check for upcoming regulatory deadlines (daily).

	Called by scheduler_events["daily"].
	Sends notifications for deadlines within 30, 14, and 7 days.
	"""
	from .notifications.alert_manager import RegulatoryAlertManager

	alert_manager = RegulatoryAlertManager()

	# Notify for different urgency levels
	for days in [30, 14, 7]:
		alert_manager.notify_upcoming_effective_date(days_ahead=days)


def generate_regulatory_digest():
	"""
	Generate and send weekly regulatory digest (weekly).

	Called by scheduler_events["weekly"].
	Sends summary email to compliance stakeholders.
	"""
	from .notifications.alert_manager import RegulatoryAlertManager

	alert_manager = RegulatoryAlertManager()
	alert_manager.send_weekly_digest()


def cleanup_old_updates():
	"""
	Archive old regulatory updates (monthly).

	Called by scheduler_events["monthly"].
	Marks updates older than 2 years as archived.
	"""
	from frappe.utils import add_days, nowdate

	cutoff_date = add_days(nowdate(), -730)  # 2 years

	# Find old implemented updates
	old_updates = frappe.get_all(
		"Regulatory Update",
		filters={"status": "Implemented", "publication_date": ["<", cutoff_date]},
		pluck="name",
	)

	# Archive (could be status change or actual archival)
	for update_name in old_updates:
		frappe.db.set_value("Regulatory Update", update_name, "status", "Not Applicable")

	frappe.db.commit()

	if old_updates:
		frappe.logger().info(f"Archived {len(old_updates)} old regulatory updates")
