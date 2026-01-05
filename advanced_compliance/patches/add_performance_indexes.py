# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Patch to add performance indexes to Advanced Compliance tables.
"""

import frappe


def execute():
	"""Add performance indexes to compliance tables."""

	indexes = [
		# Control Activity indexes
		("tabControl Activity", "idx_control_status", "status"),
		("tabControl Activity", "idx_control_owner", "control_owner"),
		("tabControl Activity", "idx_control_key", "is_key_control"),
		# Risk Register Entry indexes
		("tabRisk Register Entry", "idx_risk_status", "status"),
		# Test Execution indexes
		("tabTest Execution", "idx_test_status", "status"),
		("tabTest Execution", "idx_test_control", "control"),
		("tabTest Execution", "idx_test_date", "test_date"),
		# Deficiency indexes
		("tabDeficiency", "idx_deficiency_status", "status"),
		("tabDeficiency", "idx_deficiency_control", "control"),
		# Control Evidence indexes
		("tabControl Evidence", "idx_evidence_control", "control_activity"),
		# Regulatory Update indexes
		("tabRegulatory Update", "idx_regupdate_status", "status"),
		("tabRegulatory Update", "idx_regupdate_effective", "effective_date"),
		("tabRegulatory Update", "idx_regupdate_body", "regulatory_body"),
		# Graph Entity indexes
		("tabGraph Entity", "idx_graph_entity_type", "entity_type"),
		# Graph Relationship indexes
		("tabGraph Relationship", "idx_graph_rel_type", "relationship_type"),
		("tabGraph Relationship", "idx_graph_rel_source", "source_entity"),
		("tabGraph Relationship", "idx_graph_rel_target", "target_entity"),
	]

	for table, index_name, column in indexes:
		try:
			# Validate table exists using Frappe's safe method
			if not frappe.db.table_exists(table):
				frappe.logger().info(f"Table {table} does not exist, skipping index creation")
				continue

			# Check if index already exists using parameterized query
			existing_indexes = frappe.db.sql(
				"""
				SELECT DISTINCT INDEX_NAME
				FROM INFORMATION_SCHEMA.STATISTICS
				WHERE TABLE_SCHEMA = DATABASE()
				AND TABLE_NAME = %s
				AND INDEX_NAME = %s
			""",
				(table, index_name),
				as_dict=True,
			)

			if not existing_indexes:
				# Use Frappe's safe db.add_index method instead of raw SQL
				frappe.db.add_index(table, [column], index_name)
				frappe.db.commit()
				frappe.logger().info(f"Created index {index_name} on {table}.{column}")

		except Exception as e:
			# Log but don't fail - index might already exist or column might not exist
			frappe.log_error(
				message=f"Failed to create index {index_name} on {table}: {str(e)}\n{frappe.get_traceback()}",
				title="Performance Index Creation Error",
			)
