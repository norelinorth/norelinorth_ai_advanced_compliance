"""
NL Query Log DocType Controller.

Logs natural language queries for analysis and improvement.
"""

import json

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class NLQueryLog(Document):
	"""Controller for NL Query Log DocType."""

	def before_insert(self):
		"""Set defaults."""
		if not self.query_time:
			self.query_time = now_datetime()
		if not self.user:
			self.user = frappe.session.user

	@staticmethod
	def log_query(
		question,
		parsed_intent=None,
		generated_query=None,
		response=None,
		response_data=None,
		query_time_ms=None,
	):
		"""
		Log a natural language query.

		Args:
		    question: The original question
		    parsed_intent: Parsed intent dict
		    generated_query: Generated SQL/ORM query
		    response: Natural language response
		    response_data: Structured response data
		    query_time_ms: Processing time in ms

		Returns:
		    NL Query Log document
		"""
		log = frappe.get_doc(
			{
				"doctype": "NL Query Log",
				"question": question,
				"parsed_intent": json.dumps(parsed_intent) if parsed_intent else None,
				"generated_query": generated_query,
				"response": response,
				"response_data": json.dumps(response_data) if response_data else None,
				"query_time_ms": query_time_ms,
			}
		)
		log.insert(ignore_permissions=True)
		return log

	@staticmethod
	def get_query_stats():
		"""Get query statistics."""
		stats = {
			"total_queries": frappe.db.count("NL Query Log"),
			"helpful_count": frappe.db.count("NL Query Log", {"feedback": "Helpful"}),
			"not_helpful_count": frappe.db.count("NL Query Log", {"feedback": "Not Helpful"}),
			"avg_response_time_ms": 0,
		}

		# Calculate average response time
		avg_time = frappe.db.sql(
			"""
            SELECT AVG(query_time_ms) as avg_time
            FROM `tabNL Query Log`
            WHERE query_time_ms IS NOT NULL
        """,
			as_dict=True,
		)

		if avg_time and len(avg_time) > 0 and avg_time[0].avg_time:
			stats["avg_response_time_ms"] = round(avg_time[0].avg_time, 2)

		return stats
