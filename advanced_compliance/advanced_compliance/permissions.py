"""
Custom permission handlers for Advanced Compliance.

These functions are called by Frappe's permission system via hooks.py.
"""

import frappe


def control_activity_query(user):
	"""
	Permission query for Control Activity list view.

	Returns SQL condition to filter records based on user role.
	"""
	if not user:
		user = frappe.session.user

	# Admins see everything
	if "System Manager" in frappe.get_roles(user) or "Compliance Admin" in frappe.get_roles(user):
		return ""

	# Control owners see only their controls
	if "Control Owner" in frappe.get_roles(user):
		return f"`tabControl Activity`.control_owner = {frappe.db.escape(user)}"

	# Default: show all (read permission handled by DocType permissions)
	return ""


def risk_entry_query(user):
	"""Permission query for Risk Register Entry list view."""
	if not user:
		user = frappe.session.user

	if "System Manager" in frappe.get_roles(user) or "Compliance Admin" in frappe.get_roles(user):
		return ""

	return ""


def test_execution_query(user):
	"""Permission query for Test Execution list view."""
	if not user:
		user = frappe.session.user

	if "System Manager" in frappe.get_roles(user) or "Compliance Admin" in frappe.get_roles(user):
		return ""

	# Internal auditors see their tests
	if "Internal Auditor" in frappe.get_roles(user):
		return f"`tabTest Execution`.tester = {frappe.db.escape(user)}"

	return ""


def deficiency_query(user):
	"""Permission query for Deficiency list view."""
	if not user:
		user = frappe.session.user

	if "System Manager" in frappe.get_roles(user) or "Compliance Admin" in frappe.get_roles(user):
		return ""

	return ""


def control_activity_permission(doc, ptype=None, user=None, debug=False):
	"""
	Document-level permission check for Control Activity.

	Args:
	    doc: The Control Activity document
	    ptype: Type of permission (read, write, etc.)
	    user: User to check permission for
	    debug: Debug flag

	Returns:
	    True if user has permission, False otherwise

	Note: Frappe v16 requires explicit True/False return - None no longer falls back
	"""
	if not user:
		user = frappe.session.user

	roles = frappe.get_roles(user)

	# Admins have full access
	if "System Manager" in roles or "Compliance Admin" in roles:
		return True

	# Control owners can read and edit their controls
	if "Control Owner" in roles:
		if ptype == "read":
			return True  # Can read all controls
		if ptype in ["write", "submit"]:
			return doc.control_owner == user  # Can only edit own controls

	# Internal Auditor can read all controls
	if "Internal Auditor" in roles and ptype == "read":
		return True

	# Compliance Officer and Viewer can read
	if ptype == "read" and ("Compliance Officer" in roles or "Compliance Viewer" in roles):
		return True

	# Default: deny access (let DocType permissions handle it via role permissions)
	return False


def test_execution_permission(doc, ptype=None, user=None, debug=False):
	"""
	Document-level permission check for Test Execution.

	Note: Frappe v16 requires explicit True/False return - None no longer falls back
	"""
	if not user:
		user = frappe.session.user

	roles = frappe.get_roles(user)

	# Admins have full access
	if "System Manager" in roles or "Compliance Admin" in roles:
		return True

	# Internal auditors can read all and submit/cancel their tests
	if "Internal Auditor" in roles:
		if ptype == "read":
			return True
		if ptype in ["submit", "cancel", "write"]:
			return doc.tester == user

	# Compliance Officer and Viewer can read
	if ptype == "read" and ("Compliance Officer" in roles or "Compliance Viewer" in roles):
		return True

	# Control Owner can read
	if ptype == "read" and "Control Owner" in roles:
		return True

	# Default: deny access
	return False
