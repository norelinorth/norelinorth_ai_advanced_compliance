#!/usr/bin/env python3
"""Check what demo data exists in the database."""

import frappe


def check_demo_data():
	"""Check current demo data in database."""

	frappe.set_user("Administrator")

	print("=" * 60)
	print("CURRENT DEMO DATA STATUS")
	print("=" * 60)

	controls = frappe.db.count("Control Activity")
	risks = frappe.db.count("Risk Register Entry")
	coso = frappe.db.count("COSO Principle")

	print(f"\nControl Activities: {controls}")
	print(f"Risk Register Entries: {risks}")
	print(f"COSO Principles: {coso}")

	if controls > 0:
		print("\n--- Sample Control Names ---")
		for ctrl in frappe.db.get_all("Control Activity", fields=["control_name"], limit=10):
			print(f"  {ctrl.control_name}")

	if risks > 0:
		print("\n--- Sample Risk Names ---")
		for risk in frappe.db.get_all("Risk Register Entry", fields=["risk_name"], limit=10):
			print(f"  {risk.risk_name}")

	print("\n" + "=" * 60)


if __name__ == "__main__":
	check_demo_data()
