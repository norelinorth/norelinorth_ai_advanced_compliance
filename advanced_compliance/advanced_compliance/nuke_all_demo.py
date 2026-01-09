#!/usr/bin/env python3
"""
Nuclear option: Delete ALL demo data and start fresh.
"""

import frappe


def nuke_all_demo():
	"""Delete ALL controls, risks, and related data."""

	frappe.set_user("Administrator")

	deleted = {
		"deficiencies": 0,
		"tests": 0,
		"controls": 0,
		"risks": 0,
		"coso": 0,
		"control_cats": 0,
		"risk_cats": 0,
	}

	print("=" * 60)
	print("NUCLEAR OPTION: DELETING ALL DEMO DATA")
	print("=" * 60)

	# Delete all Deficiencies
	print("\n1. Deleting ALL Deficiencies...")
	for name in frappe.get_all("Deficiency", pluck="name"):
		try:
			frappe.delete_doc("Deficiency", name, force=True)
			deleted["deficiencies"] += 1
		except Exception:
			pass

	# Delete all Test Executions
	print("\n2. Deleting ALL Test Executions...")
	for name in frappe.get_all("Test Execution", pluck="name"):
		try:
			frappe.delete_doc("Test Execution", name, force=True)
			deleted["tests"] += 1
		except Exception:
			pass

	# Delete all Control Activities
	print("\n3. Deleting ALL Control Activities...")
	controls = frappe.get_all("Control Activity", pluck="name")
	print(f"   Found {len(controls)} controls to delete")
	for name in controls:
		try:
			frappe.delete_doc("Control Activity", name, force=True)
			deleted["controls"] += 1
			if deleted["controls"] % 20 == 0:
				print(f"   Deleted {deleted['controls']} controls...")
		except Exception as e:
			print(f"   Failed: {name}: {str(e)}")

	# Delete all Risk Register Entries
	print("\n4. Deleting ALL Risk Register Entries...")
	risks = frappe.get_all("Risk Register Entry", pluck="name")
	print(f"   Found {len(risks)} risks to delete")
	for name in risks:
		try:
			frappe.delete_doc("Risk Register Entry", name, force=True)
			deleted["risks"] += 1
			if deleted["risks"] % 20 == 0:
				print(f"   Deleted {deleted['risks']} risks...")
		except Exception as e:
			print(f"   Failed: {name}: {str(e)}")

	# Delete all COSO Principles
	print("\n5. Deleting ALL COSO Principles...")
	for name in frappe.get_all("COSO Principle", pluck="name"):
		try:
			frappe.delete_doc("COSO Principle", name, force=True)
			deleted["coso"] += 1
		except Exception:
			pass

	# Delete all Risk Categories
	print("\n6. Deleting ALL Risk Categories...")
	for name in frappe.get_all("Risk Category", pluck="name"):
		try:
			frappe.delete_doc("Risk Category", name, force=True)
			deleted["risk_cats"] += 1
		except Exception:
			pass

	# Delete all Control Categories
	print("\n7. Deleting ALL Control Categories...")
	for name in frappe.get_all("Control Category", pluck="name"):
		try:
			frappe.delete_doc("Control Category", name, force=True)
			deleted["control_cats"] += 1
		except Exception:
			pass

	frappe.db.commit()

	print("\n" + "=" * 60)
	print("SUMMARY")
	print("=" * 60)
	print(f"Deleted {deleted['deficiencies']} deficiencies")
	print(f"Deleted {deleted['tests']} test executions")
	print(f"Deleted {deleted['controls']} control activities")
	print(f"Deleted {deleted['risks']} risk register entries")
	print(f"Deleted {deleted['coso']} COSO principles")
	print(f"Deleted {deleted['risk_cats']} risk categories")
	print(f"Deleted {deleted['control_cats']} control categories")
	print(f"\nTotal: {sum(deleted.values())} records deleted")
	print("=" * 60)
	print("\nNow run:")
	print(
		'bench --site erpnext.local execute "advanced_compliance.advanced_compliance.demo.finance_accounting_data.setup_finance_accounting_data"'
	)
	print("=" * 60)

	return deleted


if __name__ == "__main__":
	nuke_all_demo()
