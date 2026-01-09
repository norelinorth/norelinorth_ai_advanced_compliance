#!/usr/bin/env python3
"""
Clear old demo data with [DEMO] prefixes.
Run this to remove the bad demo data before generating the excellent professional data.
"""

import frappe


def clear_old_demo_data():
	"""Remove all records with [DEMO] prefix."""

	frappe.set_user("Administrator")

	deleted = {
		"deficiencies": 0,
		"tests": 0,
		"controls": 0,
		"risks": 0,
		"regulatory_updates": 0,
	}

	print("=" * 60)
	print("CLEARING OLD [DEMO] DATA")
	print("=" * 60)

	# Delete Deficiencies with [DEMO] in description
	print("\n1. Checking Deficiencies...")
	if frappe.db.table_exists("tabDeficiency"):
		deficiencies = frappe.get_all(
			"Deficiency", filters=[["description", "like", "%[DEMO]%"]], pluck="name"
		)
		for name in deficiencies:
			try:
				frappe.delete_doc("Deficiency", name, force=True)
				deleted["deficiencies"] += 1
				print(f"   Deleted deficiency: {name}")
			except Exception as e:
				print(f"   Failed to delete {name}: {str(e)}")

	# Delete Test Executions linked to [DEMO] controls
	print("\n2. Checking Test Executions...")
	if frappe.db.table_exists("tabTest Execution"):
		# Get all [DEMO] control names
		demo_controls = frappe.get_all(
			"Control Activity", filters=[["control_name", "like", "%[DEMO]%"]], pluck="name"
		)
		if demo_controls:
			tests = frappe.get_all("Test Execution", filters=[["control", "in", demo_controls]], pluck="name")
			for name in tests:
				try:
					frappe.delete_doc("Test Execution", name, force=True)
					deleted["tests"] += 1
					print(f"   Deleted test: {name}")
				except Exception as e:
					print(f"   Failed to delete {name}: {str(e)}")

	# Delete Control Activities with [DEMO]
	print("\n3. Checking Control Activities...")
	if frappe.db.table_exists("tabControl Activity"):
		# Use SQL for more reliable search
		controls = frappe.db.sql(
			"""
			SELECT name, control_name
			FROM `tabControl Activity`
			WHERE control_name LIKE '%DEMO%'
			OR control_name LIKE '%[DEMO]%'
		""",
			as_dict=True,
		)
		print(f"   Found {len(controls)} control activities with [DEMO]")
		for ctrl in controls:
			try:
				frappe.delete_doc("Control Activity", ctrl.name, force=True)
				deleted["controls"] += 1
				if deleted["controls"] % 10 == 0:
					print(f"   Deleted {deleted['controls']} controls...")
			except Exception as e:
				print(f"   Failed to delete {ctrl.name}: {str(e)}")

	# Delete Risk Register Entries with [DEMO]
	print("\n4. Checking Risk Register Entries...")
	if frappe.db.table_exists("tabRisk Register Entry"):
		# Use SQL for more reliable search
		risks = frappe.db.sql(
			"""
			SELECT name, risk_name
			FROM `tabRisk Register Entry`
			WHERE risk_name LIKE '%DEMO%'
			OR risk_name LIKE '%[DEMO]%'
		""",
			as_dict=True,
		)
		print(f"   Found {len(risks)} risk register entries with [DEMO]")
		for risk in risks:
			try:
				frappe.delete_doc("Risk Register Entry", risk.name, force=True)
				deleted["risks"] += 1
				if deleted["risks"] % 10 == 0:
					print(f"   Deleted {deleted['risks']} risks...")
			except Exception as e:
				print(f"   Failed to delete {risk.name}: {str(e)}")

	# Delete Regulatory Updates with [DEMO]
	print("\n5. Checking Regulatory Updates...")
	if frappe.db.table_exists("tabRegulatory Update"):
		updates = frappe.get_all("Regulatory Update", filters=[["title", "like", "%[DEMO]%"]], pluck="name")
		for name in updates:
			try:
				frappe.delete_doc("Regulatory Update", name, force=True)
				deleted["regulatory_updates"] += 1
				print(f"   Deleted regulatory update: {name}")
			except Exception as e:
				print(f"   Failed to delete {name}: {str(e)}")

	frappe.db.commit()

	print("\n" + "=" * 60)
	print("SUMMARY")
	print("=" * 60)
	print(f"Deleted {deleted['deficiencies']} deficiencies")
	print(f"Deleted {deleted['tests']} test executions")
	print(f"Deleted {deleted['controls']} control activities")
	print(f"Deleted {deleted['risks']} risk register entries")
	print(f"Deleted {deleted['regulatory_updates']} regulatory updates")
	print(f"\nTotal: {sum(deleted.values())} records deleted")
	print("=" * 60)

	return deleted


if __name__ == "__main__":
	clear_old_demo_data()
