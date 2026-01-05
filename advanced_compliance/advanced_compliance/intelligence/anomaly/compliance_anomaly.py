"""
Compliance Anomaly Detection.

Statistical detection of unusual patterns in compliance data.
"""

import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate, nowdate


class ComplianceAnomalyDetector:
	"""
	Detects anomalies in compliance data using statistical methods.

	Anomaly Types:
	- Testing clusters: Multiple controls tested on same day
	- Pass rate changes: Sudden changes in test pass rates
	- Owner concentration: Too many controls owned by one person
	- Testing gaps: Controls not tested within expected frequency
	- Deficiency spikes: Unusual increase in deficiencies
	- Evidence staleness: Old evidence not refreshed
	"""

	# Anomaly detection thresholds
	MIN_TESTS_FOR_CLUSTER = 5  # Minimum tests to consider as cluster
	BASE_THRESHOLD_MULTIPLIER = 2.0  # Multiplier for average test count
	PASS_RATE_CHANGE_THRESHOLD = 0.3  # 30% change threshold for pass rate anomalies
	DEFICIENCY_SPIKE_MULTIPLIER = 2.0  # Deficiency increase threshold multiplier

	def __init__(self):
		"""Initialize the anomaly detector."""
		self.settings = self._get_settings()
		if self.settings:
			self.sensitivity = self.settings.get_anomaly_sensitivity_value()

			# Warn if not configured (method returns default but we should notify)
			if not self.settings.anomaly_sensitivity:
				frappe.log_error(
					message="Anomaly sensitivity not configured in AI Provider Settings. Using default (Medium).",
					title="Anomaly Detection Configuration Warning",
				)
		else:
			# No settings at all
			self.sensitivity = 1.0
			frappe.log_error(
				message="AI Provider Settings not found. Using default anomaly sensitivity (Medium).",
				title="Missing AI Provider Settings",
			)

	def _get_settings(self):
		"""Get AI provider settings."""
		try:
			from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
				get_ai_settings,
			)

			return get_ai_settings()
		except Exception:
			return None

	def detect_all_anomalies(self):
		"""
		Run all anomaly detection checks.

		Returns:
		    List of detected anomalies
		"""
		anomalies = []

		# Run all detection methods
		anomalies.extend(self.detect_testing_clusters())
		anomalies.extend(self.detect_pass_rate_changes())
		anomalies.extend(self.detect_owner_concentration())
		anomalies.extend(self.detect_testing_gaps())
		anomalies.extend(self.detect_deficiency_spikes())
		anomalies.extend(self.detect_evidence_staleness())

		return anomalies

	def detect_testing_clusters(self, days_back=30):
		"""
		Detect unusual clustering of test executions.

		This might indicate batch testing rather than proper scheduling.

		Args:
		    days_back: Number of days to analyze

		Returns:
		    List of anomalies
		"""
		anomalies = []
		from_date = add_days(nowdate(), -days_back)

		# Get test counts by date
		test_counts = frappe.db.sql(
			"""
            SELECT
                DATE(test_date) as test_day,
                COUNT(*) as test_count
            FROM `tabTest Execution`
            WHERE test_date >= %(from_date)s
            AND docstatus = 1
            GROUP BY DATE(test_date)
            ORDER BY test_count DESC
        """,
			{"from_date": from_date},
			as_dict=True,
		)

		if not test_counts:
			return anomalies

		# Calculate statistics
		counts = [tc.test_count for tc in test_counts]
		avg_count = sum(counts) / len(counts) if counts else 0
		threshold = avg_count * (self.BASE_THRESHOLD_MULTIPLIER / self.sensitivity)  # Adjusted by sensitivity

		# Find anomalous days
		for tc in test_counts:
			if tc.test_count > threshold and tc.test_count > self.MIN_TESTS_FOR_CLUSTER:
				anomalies.append(
					{
						"anomaly_type": "Testing Cluster",
						"severity": "Medium" if tc.test_count < threshold * 2 else "High",
						"title": _("Unusual testing cluster on {0}").format(tc.test_day),
						"description": _("{0} tests executed on single day (average: {1:.1f})").format(
							tc.test_count, avg_count
						),
						"details": {
							"date": str(tc.test_day),
							"test_count": tc.test_count,
							"average": avg_count,
							"threshold": threshold,
						},
						"recommended_action": _("Review testing schedule to ensure proper distribution"),
					}
				)

		return anomalies

	def detect_pass_rate_changes(self, window_days=30):
		"""
		Detect sudden changes in test pass rates.

		Significant drops might indicate control degradation.

		Args:
		    window_days: Comparison window in days

		Returns:
		    List of anomalies
		"""
		anomalies = []
		today = nowdate()
		mid_date = add_days(today, -window_days)
		start_date = add_days(today, -window_days * 2)

		# Single query to get test stats for all active controls in both periods
		# This avoids N+1 query problem
		test_stats = frappe.db.sql(
			"""
            SELECT
                te.control,
                CASE WHEN te.test_date >= %(mid_date)s THEN 'recent' ELSE 'previous' END as period,
                COUNT(*) as total,
                SUM(CASE WHEN te.test_result = 'Effective' THEN 1 ELSE 0 END) as passed
            FROM `tabTest Execution` te
            INNER JOIN `tabControl Activity` ca ON te.control = ca.name
            WHERE te.test_date >= %(start_date)s
            AND te.docstatus = 1
            AND ca.status = 'Active'
            GROUP BY te.control, period
        """,
			{"mid_date": mid_date, "start_date": start_date},
			as_dict=True,
		)

		# Build stats dictionary by control
		control_stats = {}
		for row in test_stats:
			if row.control not in control_stats:
				control_stats[row.control] = {"recent": None, "previous": None}
			control_stats[row.control][row.period] = row

		for control_id, stats in control_stats.items():
			recent = stats.get("recent")
			previous = stats.get("previous")

			# Skip if either period has no data
			if not recent or not previous:
				continue

			recent_total = recent.total
			previous_total = previous.total

			# Need minimum tests in both periods (at least 2 tests)
			if recent_total < 2 or previous_total < 2:
				continue

			# Safe to access .passed since we validated objects exist
			# flt() automatically converts NULL/None to 0.0
			recent_passed = flt(recent.passed)
			previous_passed = flt(previous.passed)

			recent_rate = recent_passed / recent_total
			previous_rate = previous_passed / previous_total

			# Detect significant drop
			rate_change = previous_rate - recent_rate
			change_threshold = self.PASS_RATE_CHANGE_THRESHOLD / self.sensitivity  # Adjusted by sensitivity

			if rate_change >= change_threshold:
				control_name = frappe.db.get_value("Control Activity", control_id, "control_name")
				anomalies.append(
					{
						"anomaly_type": "Pass Rate Drop",
						"severity": "High" if rate_change >= 0.5 else "Medium",
						"title": _("Pass rate dropped for {0}").format(control_name or control_id),
						"description": _("Pass rate dropped from {0:.0%} to {1:.0%}").format(
							previous_rate, recent_rate
						),
						"details": {
							"control_id": control_id,
							"previous_rate": previous_rate,
							"recent_rate": recent_rate,
							"change": rate_change,
						},
						"related_doctype": "Control Activity",
						"related_document": control_id,
						"recommended_action": _("Review control design and operating effectiveness"),
					}
				)

		return anomalies

	def detect_owner_concentration(self, threshold_percent=30):
		"""
		Detect when too many controls are owned by one person.

		Concentration creates single-point-of-failure risk.

		Args:
		    threshold_percent: Percentage threshold for concentration

		Returns:
		    List of anomalies
		"""
		anomalies = []

		# Get control counts by owner
		owner_counts = frappe.db.sql(
			"""
            SELECT
                control_owner,
                COUNT(*) as control_count
            FROM `tabControl Activity`
            WHERE status = 'Active'
            AND control_owner IS NOT NULL
            GROUP BY control_owner
            ORDER BY control_count DESC
        """,
			as_dict=True,
		)

		if not owner_counts:
			return anomalies

		total_controls = sum(oc.control_count for oc in owner_counts)
		if total_controls == 0:
			return anomalies

		adjusted_threshold = threshold_percent / self.sensitivity

		for oc in owner_counts:
			concentration = (oc.control_count / total_controls) * 100

			if concentration >= adjusted_threshold:
				owner_name = frappe.db.get_value("User", oc.control_owner, "full_name")
				anomalies.append(
					{
						"anomaly_type": "Owner Concentration",
						"severity": "High" if concentration >= 50 else "Medium",
						"title": _("High control concentration for {0}").format(
							owner_name or oc.control_owner
						),
						"description": _("{0} owns {1:.0%} of all active controls ({2} controls)").format(
							owner_name or oc.control_owner, concentration / 100, oc.control_count
						),
						"details": {
							"owner": oc.control_owner,
							"control_count": oc.control_count,
							"total_controls": total_controls,
							"concentration_percent": concentration,
						},
						"related_doctype": "User",
						"related_document": oc.control_owner,
						"recommended_action": _(
							"Consider distributing control ownership to reduce key person risk"
						),
					}
				)

		return anomalies

	def detect_testing_gaps(self):
		"""
		Detect controls not tested within expected frequency.

		Returns:
		    List of anomalies
		"""
		anomalies = []
		today = nowdate()

		frequency_days = {"Monthly": 30, "Quarterly": 90, "Semi-annually": 180, "Annually": 365}

		# Get controls with test frequency
		controls = frappe.get_all(
			"Control Activity",
			filters={"status": "Active", "test_frequency": ["is", "set"]},
			fields=["name", "control_name", "test_frequency", "last_test_date"],
		)

		for control in controls:
			expected_days = frequency_days.get(control.test_frequency)
			if not expected_days:
				continue

			if control.last_test_date:
				days_since = date_diff(today, control.last_test_date)
			else:
				days_since = 999  # Never tested

			# Apply sensitivity to threshold
			overdue_threshold = expected_days * (1.0 / self.sensitivity)

			if days_since > overdue_threshold:
				severity = "Critical" if days_since > expected_days * 2 else "High"
				anomalies.append(
					{
						"anomaly_type": "Testing Gap",
						"severity": severity,
						"title": _("Overdue testing for {0}").format(control.control_name or control.name),
						"description": _("{0} days since last test (expected: every {1} days)").format(
							days_since, expected_days
						),
						"details": {
							"control_id": control.name,
							"last_test_date": str(control.last_test_date) if control.last_test_date else None,
							"days_since_test": days_since,
							"expected_frequency_days": expected_days,
							"test_frequency": control.test_frequency,
						},
						"related_doctype": "Control Activity",
						"related_document": control.name,
						"recommended_action": _("Schedule control testing immediately"),
					}
				)

		return anomalies

	def detect_deficiency_spikes(self, window_days=30):
		"""
		Detect unusual increases in deficiency creation.

		A spike might indicate systemic control issues.

		Args:
		    window_days: Analysis window in days

		Returns:
		    List of anomalies
		"""
		anomalies = []
		today = nowdate()
		mid_date = add_days(today, -window_days)
		start_date = add_days(today, -window_days * 2)

		# Recent period deficiencies
		recent_count = frappe.db.count("Deficiency", {"creation": [">=", mid_date]})

		# Previous period deficiencies - use SQL for date range
		result = frappe.db.sql(
			"""
            SELECT COUNT(*) FROM `tabDeficiency`
            WHERE creation >= %(start_date)s AND creation < %(mid_date)s
        """,
			{"start_date": start_date, "mid_date": mid_date},
		)
		previous_count = result[0][0] if result and len(result) > 0 else 0

		# Skip if no baseline data
		if not previous_count or previous_count == 0:
			return anomalies

		# Safe division with type conversion
		increase_ratio = flt(recent_count) / flt(previous_count)

		# Handle edge cases (NaN, Infinity)
		if not increase_ratio or increase_ratio == float("inf"):
			return anomalies

		# Detect significant increase (default: 2x)
		spike_threshold = self.DEFICIENCY_SPIKE_MULTIPLIER / self.sensitivity

		if increase_ratio >= spike_threshold and recent_count > self.MIN_TESTS_FOR_CLUSTER:
			anomalies.append(
				{
					"anomaly_type": "Deficiency Spike",
					"severity": "High" if increase_ratio >= 3 else "Medium",
					"title": _("Significant increase in deficiencies"),
					"description": _(
						"{0} deficiencies in last {1} days vs {2} in prior period ({3:.1f}x increase)"
					).format(recent_count, window_days, previous_count, increase_ratio),
					"details": {
						"recent_count": recent_count,
						"previous_count": previous_count,
						"increase_ratio": increase_ratio,
						"window_days": window_days,
					},
					"recommended_action": _("Investigate root cause of increased deficiencies"),
				}
			)

		return anomalies

	def detect_evidence_staleness(self, stale_days=180):
		"""
		Detect controls with old evidence not refreshed.

		Stale evidence might indicate ineffective control monitoring.

		Args:
		    stale_days: Days after which evidence is considered stale

		Returns:
		    List of anomalies
		"""
		anomalies = []
		stale_date = add_days(nowdate(), -stale_days)

		# Find controls where newest evidence is older than threshold
		# Using creation date as the evidence timestamp
		stale_evidence = frappe.db.sql(
			"""
            SELECT
                ca.name as control_id,
                ca.control_name,
                MAX(ce.creation) as latest_evidence_date
            FROM `tabControl Activity` ca
            LEFT JOIN `tabControl Evidence` ce ON ce.control_activity = ca.name
            WHERE ca.status = 'Active'
            GROUP BY ca.name, ca.control_name
            HAVING latest_evidence_date < %(stale_date)s
            OR latest_evidence_date IS NULL
        """,
			{"stale_date": stale_date},
			as_dict=True,
		)

		for item in stale_evidence:
			days_stale = None
			if item.latest_evidence_date:
				days_stale = date_diff(nowdate(), item.latest_evidence_date)

			anomalies.append(
				{
					"anomaly_type": "Evidence Staleness",
					"severity": "Medium",
					"title": _("Stale evidence for {0}").format(item.control_name or item.control_id),
					"description": _("No evidence collected in {0} days").format(
						days_stale or "N/A (never collected)"
					),
					"details": {
						"control_id": item.control_id,
						"latest_evidence_date": str(item.latest_evidence_date)
						if item.latest_evidence_date
						else None,
						"days_since_evidence": days_stale,
					},
					"related_doctype": "Control Activity",
					"related_document": item.control_id,
					"recommended_action": _("Collect fresh evidence for this control"),
				}
			)

		return anomalies

	def create_alerts_from_anomalies(self, anomalies):
		"""
		Create Compliance Alert documents from detected anomalies.

		Args:
		    anomalies: List of anomaly dicts

		Returns:
		    List of created alert names
		"""
		from advanced_compliance.advanced_compliance.doctype.compliance_alert.compliance_alert import (
			ComplianceAlert,
		)

		# Map anomaly severity to alert severity (Info, Warning, Critical)
		severity_map = {"Low": "Info", "Medium": "Warning", "High": "Critical", "Critical": "Critical"}

		created_alerts = []

		for anomaly in anomalies:
			# Build description with recommended action if available
			description = anomaly.get("description", "")
			if anomaly.get("recommended_action"):
				description += f"\n\nRecommended Action: {anomaly.get('recommended_action')}"

			# Map severity to valid alert severity
			anomaly_severity = anomaly.get("severity", "Medium")
			alert_severity = severity_map.get(anomaly_severity, "Warning")

			alert = ComplianceAlert.create_alert(
				alert_type="Anomaly",
				severity=alert_severity,
				title=anomaly.get("title"),
				description=description,
				related_doctype=anomaly.get("related_doctype"),
				related_document=anomaly.get("related_document"),
				detection_details=anomaly.get("details"),
			)
			created_alerts.append(alert.name)

		return created_alerts


# API Endpoints
@frappe.whitelist()
def run_anomaly_detection():
	"""
	API endpoint to run all anomaly detection.

	Returns:
	    List of detected anomalies
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("anomaly_detection"):
		frappe.throw(_("Anomaly detection is not enabled"))

	if not frappe.has_permission("Compliance Alert", "read"):
		frappe.throw(_("No permission to view compliance alerts"))

	detector = ComplianceAnomalyDetector()
	return detector.detect_all_anomalies()


@frappe.whitelist()
def run_anomaly_detection_with_alerts():
	"""
	API endpoint to run anomaly detection and create alerts.

	Returns:
	    Summary with anomalies and created alerts
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("anomaly_detection"):
		frappe.throw(_("Anomaly detection is not enabled"))

	if not frappe.has_permission("Compliance Alert", "create"):
		frappe.throw(_("No permission to create compliance alerts"))

	detector = ComplianceAnomalyDetector()
	anomalies = detector.detect_all_anomalies()

	if anomalies:
		created_alerts = detector.create_alerts_from_anomalies(anomalies)
		frappe.db.commit()
	else:
		created_alerts = []

	# Count by type
	by_type = defaultdict(int)
	for a in anomalies:
		by_type[a.get("anomaly_type", "Unknown")] += 1

	return {
		"total_anomalies": len(anomalies),
		"alerts_created": len(created_alerts),
		"by_type": dict(by_type),
		"anomalies": anomalies,
	}


@frappe.whitelist()
def detect_specific_anomaly(anomaly_type):
	"""
	API endpoint to detect a specific type of anomaly.

	Args:
	    anomaly_type: Type of anomaly to detect

	Returns:
	    List of detected anomalies
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("anomaly_detection"):
		frappe.throw(_("Anomaly detection is not enabled"))

	if not frappe.has_permission("Compliance Alert", "read"):
		frappe.throw(_("No permission to view compliance alerts"))

	detector = ComplianceAnomalyDetector()

	detection_methods = {
		"Testing Cluster": detector.detect_testing_clusters,
		"Pass Rate Drop": detector.detect_pass_rate_changes,
		"Owner Concentration": detector.detect_owner_concentration,
		"Testing Gap": detector.detect_testing_gaps,
		"Deficiency Spike": detector.detect_deficiency_spikes,
		"Evidence Staleness": detector.detect_evidence_staleness,
	}

	method = detection_methods.get(anomaly_type)
	if not method:
		frappe.throw(_("Unknown anomaly type: {0}").format(anomaly_type))

	return method()
