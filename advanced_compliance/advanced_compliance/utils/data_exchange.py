"""
Data Exchange Utilities for Advanced Compliance

Provides APIs for bulk import/export of compliance data.
Follows standard Frappe patterns for data exchange.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

# DocTypes that support bulk export/import
EXPORTABLE_DOCTYPES = [
	"Control Category",
	"Risk Category",
	"COSO Principle",
	"Control Activity",
	"Risk Register Entry",
	"Deficiency",
	"Evidence Capture Rule",
	"Regulatory Feed Source",
]


@frappe.whitelist()
def export_compliance_data(doctypes=None, include_master_data=True, format="json"):
	"""
	Export compliance data to JSON format.

	Args:
	    doctypes: List of DocTypes to export (default: all exportable)
	    include_master_data: Include master data (categories, COSO principles)
	    format: Export format (json only for now)

	Returns:
	    dict: Export data with metadata
	"""
	if not frappe.has_permission("Control Activity", "read"):
		frappe.throw(_("You don't have permission to export compliance data"))

	if doctypes:
		if isinstance(doctypes, str):
			doctypes = json.loads(doctypes)
		# Validate requested doctypes
		for dt in doctypes:
			if dt not in EXPORTABLE_DOCTYPES:
				frappe.throw(_("DocType {0} is not exportable").format(dt))
	else:
		doctypes = EXPORTABLE_DOCTYPES.copy()

	# Master data first (for proper import order)
	master_data_doctypes = ["Control Category", "Risk Category", "COSO Principle"]

	export_data = {
		"metadata": {
			"exported_at": str(now_datetime()),
			"exported_by": frappe.session.user,
			"app_version": frappe.get_attr("advanced_compliance.hooks.app_version"),
			"frappe_version": frappe.__version__,
		},
		"data": {},
	}

	# Export master data first if included
	if include_master_data:
		for dt in master_data_doctypes:
			if dt in doctypes:
				export_data["data"][dt] = get_doctype_data(dt)
				doctypes.remove(dt)

	# Export remaining doctypes
	for dt in doctypes:
		export_data["data"][dt] = get_doctype_data(dt)

	return export_data


def get_doctype_data(doctype):
	"""Get all documents of a DocType for export."""
	# Get all field names (exclude system fields and Table fields)
	meta = frappe.get_meta(doctype)
	fields = [
		df.fieldname
		for df in meta.fields
		if df.fieldtype not in ("Section Break", "Column Break", "Tab Break", "HTML", "Button", "Table")
	]

	# Always include name
	if "name" not in fields:
		fields.insert(0, "name")

	docs = frappe.get_all(doctype, fields=fields, order_by="creation asc")

	# Handle child tables
	for doc in docs:
		for df in meta.fields:
			if df.fieldtype == "Table":
				child_meta = frappe.get_meta(df.options)
				child_fields = [
					cdf.fieldname
					for cdf in child_meta.fields
					if cdf.fieldtype not in ("Section Break", "Column Break", "Tab Break", "HTML", "Button")
				]
				doc[df.fieldname] = frappe.get_all(
					df.options, filters={"parent": doc["name"]}, fields=child_fields, order_by="idx asc"
				)

	return docs


@frappe.whitelist()
def import_compliance_data(data, update_existing=False):
	"""
	Import compliance data from JSON.

	Args:
	    data: JSON data to import
	    update_existing: If True, update existing documents

	Returns:
	    dict: Import results with counts
	"""
	if not frappe.has_permission("Control Activity", "create"):
		frappe.throw(_("You don't have permission to import compliance data"))

	if isinstance(data, str):
		data = json.loads(data)

	results = {"created": {}, "updated": {}, "skipped": {}, "errors": []}

	# Import order matters - master data first
	import_order = [
		"Control Category",
		"Risk Category",
		"COSO Principle",
		"Control Activity",
		"Risk Register Entry",
		"Deficiency",
		"Evidence Capture Rule",
		"Regulatory Feed Source",
	]

	for doctype in import_order:
		if doctype not in data.get("data", {}):
			continue

		docs = data["data"][doctype]
		results["created"][doctype] = 0
		results["updated"][doctype] = 0
		results["skipped"][doctype] = 0

		for doc_data in docs:
			try:
				import_single_document(doctype, doc_data, update_existing, results)
			except Exception as e:
				results["errors"].append({"doctype": doctype, "name": doc_data.get("name"), "error": str(e)})

	frappe.db.commit()
	return results


def import_single_document(doctype, doc_data, update_existing, results):
	"""Import a single document."""
	doc_name = doc_data.get("name")

	# Check if document exists
	if frappe.db.exists(doctype, doc_name):
		if update_existing:
			doc = frappe.get_doc(doctype, doc_name)
			doc.update(doc_data)
			doc.flags.ignore_permissions = True
			doc.save()
			results["updated"][doctype] += 1
		else:
			results["skipped"][doctype] += 1
	else:
		doc = frappe.get_doc({"doctype": doctype, **doc_data})
		doc.flags.ignore_permissions = True
		doc.insert()
		results["created"][doctype] += 1


@frappe.whitelist()
def get_export_template(doctype):
	"""
	Get an import template for a DocType.

	Args:
	    doctype: DocType to get template for

	Returns:
	    dict: Template with field definitions
	"""
	if doctype not in EXPORTABLE_DOCTYPES:
		frappe.throw(_("DocType {0} is not exportable").format(doctype))

	meta = frappe.get_meta(doctype)

	fields = []
	for df in meta.fields:
		if df.fieldtype in ("Section Break", "Column Break", "Tab Break", "HTML", "Button"):
			continue

		field_info = {
			"fieldname": df.fieldname,
			"label": df.label,
			"fieldtype": df.fieldtype,
			"reqd": df.reqd,
			"options": df.options,
			"description": df.description,
		}
		fields.append(field_info)

	return {
		"doctype": doctype,
		"fields": fields,
		"sample_data": get_doctype_data(doctype)[:3],  # First 3 records as sample
	}


@frappe.whitelist()
def get_exportable_doctypes():
	"""Get list of DocTypes that can be exported."""
	return EXPORTABLE_DOCTYPES
