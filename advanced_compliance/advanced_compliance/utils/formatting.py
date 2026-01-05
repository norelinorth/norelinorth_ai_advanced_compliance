# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Formatting utilities for Advanced Compliance

Provides locale-aware formatting for dates, currencies, and numbers.
"""

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, format_date, format_datetime


def format_for_locale(value, value_type, options=None):
	"""
	Format value according to user's locale settings.

	Args:
		value: Value to format
		value_type: Type of value (date, datetime, currency, percent, number)
		options: Additional formatting options

	Returns:
		str: Formatted value
	"""
	if value is None:
		return ""

	options = options or {}

	if value_type == "date":
		return format_date(value)

	elif value_type == "datetime":
		return format_datetime(value)

	elif value_type == "currency":
		currency = options.get("currency") or frappe.db.get_default("currency")
		if not currency:
			frappe.log_error(
				message=_("No default currency configured. Please set default currency in System Settings."),
				title="Formatting Error",
			)
			return str(value)  # Return raw value without currency formatting
		return fmt_money(value, currency=currency)

	elif value_type == "percent":
		precision = options.get("precision", 1)
		return f"{flt(value, precision)}%"

	elif value_type == "number":
		precision = options.get("precision", 2)
		return f"{flt(value, precision):,}"

	return str(value)


def format_risk_score(score):
	"""
	Format risk score with color indicator.

	Args:
		score: Risk score (1-25)

	Returns:
		dict: Score with color and label
	"""
	score = flt(score)

	if score >= 20:
		return {"score": score, "color": "red", "label": _("Critical")}
	elif score >= 15:
		return {"score": score, "color": "orange", "label": _("High")}
	elif score >= 10:
		return {"score": score, "color": "yellow", "label": _("Medium")}
	elif score >= 5:
		return {"score": score, "color": "blue", "label": _("Low")}
	else:
		return {"score": score, "color": "green", "label": _("Very Low")}


def format_control_status(status):
	"""
	Format control status with color.

	Args:
		status: Control status

	Returns:
		dict: Status with color
	"""
	status_colors = {
		"Draft": "gray",
		"Active": "green",
		"Under Review": "orange",
		"Needs Improvement": "yellow",
		"Deprecated": "red",
	}

	return {"status": status, "color": status_colors.get(status, "gray"), "label": _(status)}


def format_test_result(result):
	"""
	Format test result with color.

	Args:
		result: Test result

	Returns:
		dict: Result with color
	"""
	result_colors = {
		"Passed": "green",
		"Failed": "red",
		"Partially Passed": "yellow",
		"Not Tested": "gray",
		"Inconclusive": "orange",
	}

	return {"result": result, "color": result_colors.get(result, "gray"), "label": _(result)}


def format_deficiency_severity(severity):
	"""
	Format deficiency severity with color.

	Args:
		severity: Deficiency severity

	Returns:
		dict: Severity with color and priority
	"""
	severity_info = {
		"Critical": {"color": "red", "priority": 1, "icon": "alert-circle"},
		"Major": {"color": "orange", "priority": 2, "icon": "alert-triangle"},
		"Moderate": {"color": "yellow", "priority": 3, "icon": "info"},
		"Minor": {"color": "blue", "priority": 4, "icon": "info"},
	}

	info = severity_info.get(severity, {"color": "gray", "priority": 5, "icon": "info"})

	return {"severity": severity, "label": _(severity), **info}


def format_days_until(date, show_overdue=True):
	"""
	Format days until a date with urgency indicator.

	Args:
		date: Target date
		show_overdue: Whether to show negative days as overdue

	Returns:
		dict: Days with color and message
	"""
	from frappe.utils import date_diff, getdate, nowdate

	if not date:
		return {"days": None, "color": "gray", "message": _("No date set")}

	days = date_diff(getdate(date), getdate(nowdate()))

	if days < 0:
		if show_overdue:
			return {"days": abs(days), "color": "red", "message": _("{0} days overdue").format(abs(days))}
		else:
			return {"days": 0, "color": "gray", "message": _("Past")}

	elif days == 0:
		return {"days": 0, "color": "red", "message": _("Due today")}

	elif days <= 7:
		return {"days": days, "color": "orange", "message": _("{0} days").format(days)}

	elif days <= 30:
		return {"days": days, "color": "yellow", "message": _("{0} days").format(days)}

	else:
		return {"days": days, "color": "green", "message": _("{0} days").format(days)}


def format_percentage_change(current, previous):
	"""
	Format percentage change between two values.

	Args:
		current: Current value
		previous: Previous value

	Returns:
		dict: Change with direction and color
	"""
	if not previous:
		return {"change": 0, "direction": "neutral", "color": "gray", "label": _("N/A")}

	change = ((flt(current) - flt(previous)) / flt(previous)) * 100

	if change > 0:
		return {
			"change": round(change, 1),
			"direction": "up",
			"color": "green",
			"label": f"+{round(change, 1)}%",
		}
	elif change < 0:
		return {
			"change": round(change, 1),
			"direction": "down",
			"color": "red",
			"label": f"{round(change, 1)}%",
		}
	else:
		return {"change": 0, "direction": "neutral", "color": "gray", "label": "0%"}
