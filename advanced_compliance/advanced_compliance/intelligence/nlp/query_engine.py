"""
Natural Language Query Engine.

Allows users to ask compliance questions in plain English.
"""

import json
import re
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, nowdate


class NLQueryEngine:
	"""
	Natural language interface for compliance queries.

	Supports questions like:
	- "Show me all high risk controls"
	- "Which controls failed testing last month?"
	- "What are the open deficiencies for SOX?"
	- "List controls owned by John Smith"
	- "How many tests were executed this quarter?"
	"""

	# Query intent patterns
	INTENT_PATTERNS = {
		"list_controls": [
			r"(show|list|get|find|display)\s+(me\s+)?(all\s+)?controls?",
			r"what\s+(are\s+)?the\s+controls?",
			r"which\s+controls?",
		],
		"list_risks": [
			r"(show|list|get|find|display)\s+(me\s+)?(all\s+)?risks?",
			r"what\s+(are\s+)?the\s+risks?",
			r"which\s+risks?",
		],
		"list_deficiencies": [
			r"(show|list|get|find|display)\s+(me\s+)?(all\s+)?(open\s+)?deficienc(y|ies)",
			r"what\s+(are\s+)?the\s+(open\s+)?deficienc(y|ies)",
			r"which\s+deficienc(y|ies)",
		],
		"list_tests": [
			r"(show|list|get|find|display)\s+(me\s+)?(all\s+)?test(s|ing)?",
			r"what\s+test(s|ing)?",
			r"which\s+test(s)?",
		],
		"count": [r"how\s+many", r"count\s+(of\s+)?", r"total\s+(number\s+)?(of\s+)?"],
		"status": [r"status\s+(of|for)", r"what\s+is\s+the\s+status", r"current\s+state"],
		"failed": [r"fail(ed|ing|ure)?", r"did\s+not\s+pass", r"unsuccessful"],
		"overdue": [r"overdue", r"late", r"behind\s+schedule", r"past\s+due"],
		"high_risk": [r"high\s*risk", r"critical", r"high\s+priority"],
	}

	# Entity extraction patterns
	ENTITY_PATTERNS = {
		"framework": [
			r"(sox|sarbanes.?oxley)",
			r"(iso\s*27001|iso27001)",
			r"(gdpr)",
			r"(hipaa)",
			r"(pci.?dss|pci)",
			r"(nist)",
		],
		"time_period": [
			r"(last|this|past)\s+(week|month|quarter|year)",
			r"(today|yesterday)",
			r"(\d+)\s+(days?|weeks?|months?)\s+ago",
			r"(in|during)\s+(\d{4})",
		],
		"owner": [r"(owned\s+by|assigned\s+to|belonging\s+to)\s+([a-zA-Z\s]+)", r"([a-zA-Z]+)'s\s+controls?"],
		"status_value": [r"(active|inactive|draft|archived)", r"(open|closed|pending|resolved)"],
		"control_type": [r"(preventive|detective|corrective)", r"(manual|automated|semi.?automated)"],
	}

	def __init__(self):
		"""Initialize the NL query engine."""
		self.settings = self._get_settings()

	def _get_settings(self):
		"""Get AI provider settings."""
		try:
			from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
				get_ai_settings,
			)

			return get_ai_settings()
		except Exception:
			return None

	def query(self, question, use_llm=False):
		"""
		Process a natural language query.

		Args:
		    question: Natural language question
		    use_llm: Whether to use LLM for complex queries

		Returns:
		    Query result dict
		"""
		# Parse the question
		parsed = self.parse_question(question)

		# Execute the query
		if use_llm and self.settings and self.settings.enable_nl_queries:
			result = self._execute_llm_query(question, parsed)
		else:
			result = self._execute_rule_based_query(parsed)

		# Log the query
		self._log_query(question, parsed, result)

		return result

	def parse_question(self, question):
		"""
		Parse a question to extract intent and entities.

		Args:
		    question: Natural language question

		Returns:
		    Parsed query dict
		"""
		question_lower = question.lower().strip()

		parsed = {
			"original_question": question,
			"intents": [],
			"entities": {},
			"doctype": None,
			"filters": {},
			"is_count_query": False,
			"limit": 50,
		}

		# Extract intents
		for intent, patterns in self.INTENT_PATTERNS.items():
			for pattern in patterns:
				if re.search(pattern, question_lower):
					parsed["intents"].append(intent)
					break

		# Extract entities
		for entity_type, patterns in self.ENTITY_PATTERNS.items():
			for pattern in patterns:
				match = re.search(pattern, question_lower)
				if match:
					parsed["entities"][entity_type] = match.group(0)
					break

		# Determine target DocType
		parsed["doctype"] = self._determine_doctype(parsed["intents"])

		# Build filters from entities and intents
		parsed["filters"] = self._build_filters(parsed)

		# Check if count query
		parsed["is_count_query"] = "count" in parsed["intents"]

		return parsed

	def _determine_doctype(self, intents):
		"""Determine which DocType to query based on intents."""
		intent_to_doctype = {
			"list_controls": "Control Activity",
			"list_risks": "Risk Register Entry",
			"list_deficiencies": "Deficiency",
			"list_tests": "Test Execution",
		}

		for intent in intents:
			if intent in intent_to_doctype:
				return intent_to_doctype[intent]

		return "Control Activity"  # Default

	def _build_filters(self, parsed):
		"""Build Frappe filters from parsed entities."""
		filters = {}
		entities = parsed.get("entities", {})
		intents = parsed.get("intents", [])
		doctype = parsed.get("doctype")

		# Status filters
		if "status_value" in entities:
			status_map = {
				"active": "Active",
				"inactive": "Inactive",
				"draft": "Draft",
				"open": ["not in", ["Closed", "Cancelled"]],
				"closed": "Closed",
			}
			status = entities["status_value"].lower()
			if status in status_map:
				filters["status"] = status_map[status]
		elif doctype == "Deficiency" and "open" in parsed.get("original_question", "").lower():
			# Default to open deficiencies if not explicitly specified
			filters["status"] = ["not in", ["Closed", "Remediated"]]

		# Framework filter
		if "framework" in entities:
			framework = entities["framework"].upper()
			framework_map = {
				"SOX": "SOX",
				"SARBANES-OXLEY": "SOX",
				"ISO 27001": "ISO 27001",
				"ISO27001": "ISO 27001",
				"GDPR": "GDPR",
				"HIPAA": "HIPAA",
				"PCI-DSS": "PCI-DSS",
				"PCI": "PCI-DSS",
				"NIST": "NIST",
			}
			if framework in framework_map:
				filters["compliance_framework"] = framework_map[framework]

		# Time period filter
		if "time_period" in entities:
			date_range = self._parse_time_period(entities["time_period"])
			if date_range:
				filters["creation"] = [">=", date_range["from_date"]]

		# Intent-based filters
		if "failed" in intents and doctype == "Test Execution":
			filters["test_result"] = [
				"in",
				["Ineffective - Minor", "Ineffective - Significant", "Ineffective - Material"],
			]

		if "overdue" in intents and doctype == "Control Activity":
			# Controls with testing overdue
			filters["next_test_date"] = ["<", nowdate()]

		if "high_risk" in intents:
			if doctype == "Risk Register Entry":
				# Get high risk threshold from settings
				high_risk_threshold = frappe.db.get_single_value("Compliance Settings", "high_risk_threshold")

				if not high_risk_threshold:
					frappe.throw(_("Please configure High Risk Threshold in Compliance Settings"))

				filters["residual_risk_score"] = [">=", high_risk_threshold]
			elif doctype == "Control Activity":
				filters["is_key_control"] = 1
			elif doctype == "Deficiency":
				# Critical/high-risk deficiencies are Significant or Material severity
				filters["severity"] = ["in", ["Significant", "Material"]]

		# Control type filter
		if "control_type" in entities and doctype == "Control Activity":
			ctype = entities["control_type"].lower()
			if ctype in ["preventive", "detective", "corrective"]:
				filters["control_type"] = ctype.capitalize()
			elif ctype in ["manual", "automated", "semi-automated"]:
				automation_map = {
					"manual": "Manual",
					"automated": "Fully Automated",
					"semi-automated": "Semi-automated",
				}
				filters["automation_level"] = automation_map.get(ctype, ctype)

		return filters

	def _parse_time_period(self, time_str):
		"""Parse time period string to date range."""
		time_lower = time_str.lower()
		today = nowdate()

		if "today" in time_lower:
			return {"from_date": today, "to_date": today}

		if "yesterday" in time_lower:
			yesterday = add_days(today, -1)
			return {"from_date": yesterday, "to_date": yesterday}

		if "last week" in time_lower or "this week" in time_lower:
			return {"from_date": add_days(today, -7), "to_date": today}

		if "last month" in time_lower or "this month" in time_lower:
			return {"from_date": add_days(today, -30), "to_date": today}

		if "last quarter" in time_lower or "this quarter" in time_lower:
			return {"from_date": add_days(today, -90), "to_date": today}

		if "last year" in time_lower or "this year" in time_lower:
			return {"from_date": add_days(today, -365), "to_date": today}

		# Check for "X days/weeks/months ago"
		match = re.search(r"(\d+)\s+(days?|weeks?|months?)", time_lower)
		if match:
			num = int(match.group(1))
			unit = match.group(2)
			if "day" in unit:
				days = num
			elif "week" in unit:
				days = num * 7
			else:  # month
				days = num * 30
			return {"from_date": add_days(today, -days), "to_date": today}

		return None

	def _execute_rule_based_query(self, parsed):
		"""Execute query using rule-based approach."""
		doctype = parsed.get("doctype")
		filters = parsed.get("filters", {})
		is_count = parsed.get("is_count_query", False)
		limit = parsed.get("limit", 50)

		if not doctype:
			return {"success": False, "error": _("Could not determine what to search for")}

		# Check permission
		if not frappe.has_permission(doctype, "read"):
			return {"success": False, "error": _("No permission to access {0}").format(doctype)}

		try:
			if is_count:
				# Use get_all to respect row-level permissions (frappe.db.count bypasses them)
				results = frappe.get_all(
					doctype,
					filters=filters,
					fields=["name"],  # Minimal field fetch for performance
					limit_page_length=None,  # No pagination limit
					ignore_permissions=False,  # Respect user permissions (default)
				)
				count = len(results)

				return {
					"success": True,
					"query_type": "count",
					"doctype": doctype,
					"filters": filters,
					"count": count,
					"response": _("Found {0} {1}").format(count, doctype),
				}
			else:
				# Get field list for doctype
				fields = self._get_display_fields(doctype)

				results = frappe.get_all(
					doctype, filters=filters, fields=fields, limit=limit, order_by="modified desc"
				)

				return {
					"success": True,
					"query_type": "list",
					"doctype": doctype,
					"filters": filters,
					"count": len(results),
					"results": results,
					"response": _("Found {0} {1}").format(len(results), doctype),
				}
		except Exception as e:
			frappe.log_error(
				message=_("NL Query Error: {0}\n{1}").format(str(e), frappe.get_traceback()),
				title=_("NL Query Engine Error"),
			)
			return {
				"success": False,
				"error": _("Query could not be processed. Please try a different question."),
			}

	def _get_display_fields(self, doctype):
		"""Get relevant display fields for a DocType."""
		field_map = {
			"Control Activity": [
				"name",
				"control_name",
				"control_type",
				"status",
				"control_owner",
				"is_key_control",
				"automation_level",
				"last_test_date",
				"next_test_date",
			],
			"Risk Register Entry": [
				"name",
				"risk_name",
				"risk_category",
				"risk_owner",
				"status",
				"inherent_risk_score",
				"residual_risk_score",
			],
			"Deficiency": [
				"name",
				"description",
				"severity",
				"status",
				"control",
				"identified_date",
				"target_date",
				"remediation_owner",
			],
			"Test Execution": ["name", "control", "test_date", "test_result", "tester", "conclusion"],
		}

		return field_map.get(doctype, ["name", "creation", "modified"])

	def _execute_llm_query(self, question, parsed):
		"""
		Execute query using LLM for complex questions.

		Falls back to rule-based if LLM unavailable.
		"""
		try:
			from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
				call_llm,
				is_ai_assistant_available,
			)

			if not is_ai_assistant_available():
				return self._execute_rule_based_query(parsed)

			# Build context about available data
			context = self._build_llm_context()

			# Create prompt with better date handling instructions
			today = nowdate()
			prompt = f"""Based on the user's question, generate a JSON response with the query parameters.

Available DocTypes and their purpose:
- Control Activity: Master list of controls (has status, control_owner, is_key_control, last_test_date, next_test_date)
- Risk Register Entry: Risks and their scores (has risk_name, residual_risk_score, status)
- Test Execution: Historical test results (has control, test_date, test_result, tester)
- Deficiency: Control weaknesses found (has control, severity, status)
- Compliance Alert: System alerts (has alert_type, severity, status)
- Risk Prediction: AI PREDICTIONS for future control failures (has control, failure_probability, risk_level, is_current)

IMPORTANT DISTINCTION:
- Questions about PAST failures/tests → use Test Execution (test_result field)
- Questions about FUTURE/PREDICTED failures → use Risk Prediction (failure_probability, risk_level fields)
- "Most likely to fail" = PREDICTION = use Risk Prediction with is_current=1, order by failure_probability desc
- "Failed tests" / "Which failed" = PAST = use Test Execution

Today's date is: {today}

User Question: {question}

Filter syntax examples:
{{
  "status": "Active",
  "test_date": [">=", "2025-01-01"],
  "is_current": 1,
  "failure_probability": [">=", 0.3]
}}

Key values:
- test_result: "Effective", "Ineffective - Minor", "Ineffective - Significant", "Ineffective - Material"
- status (Control Activity): "Draft", "Active", "Under Review", "Deprecated"
- risk_level (Risk Prediction): "Low", "Medium", "High", "Critical"
- For dates use actual date strings like "{today}", not keywords like "now" or "today"

Respond with ONLY valid JSON:
- doctype: The DocType to query
- filters: Dict with field names as keys
- fields: List of fields to return
- order_by: field name with optional DESC
- limit: Result limit (default 50)"""

			# Call LLM using centralized AI Assistant
			response = call_llm(
				prompt=prompt,
				system_message="You are a compliance query assistant. Only respond with valid JSON.",
			)

			# Parse response
			try:
				query_params = json.loads(response)
			except json.JSONDecodeError:
				frappe.log_error(
					message=f"LLM returned invalid JSON: {response[:500]}", title="NL Query Engine JSON Error"
				)
				return self._execute_rule_based_query(parsed)

			# Sanitize filters - replace date keywords with actual dates
			if query_params.get("filters"):
				query_params["filters"] = self._sanitize_filters(query_params["filters"])

			# Validate DocType to prevent injection
			doctype = query_params.get("doctype")
			allowed_doctypes = [
				"Control Activity",
				"Risk Register Entry",
				"Test Execution",
				"Control Evidence",
				"Deficiency",
				"Compliance Alert",
				"Risk Prediction",
			]
			if not doctype or doctype not in allowed_doctypes:
				frappe.log_error(
					message=f"LLM returned invalid DocType: {doctype}", title="NL Query Engine DocType Error"
				)
				return self._execute_rule_based_query(parsed)

			# Execute query
			results = frappe.get_all(
				doctype,
				filters=query_params.get("filters", {}),
				fields=query_params.get("fields", ["name"]),
				order_by=query_params.get("order_by", "modified desc"),
				limit=min(query_params.get("limit", 50), 100),  # Cap at 100
			)

			return {
				"success": True,
				"query_type": "llm",
				"doctype": query_params.get("doctype"),
				"filters": query_params.get("filters"),
				"count": len(results),
				"results": results,
				"response": self._generate_ai_summary(question, doctype, results, query_params),
			}

		except Exception as e:
			frappe.log_error(message=f"LLM Query Error: {str(e)}", title=_("NL Query Engine LLM Error"))
			# Fall back to rule-based
			return self._execute_rule_based_query(parsed)

	def _sanitize_filters(self, filters):
		"""
		Sanitize LLM-generated filters.

		- Converts list-of-lists format to dict format
		- Replaces date keywords like 'today', 'now' with actual date strings.
		- Frappe's database layer doesn't understand these keywords.
		"""
		if not filters:
			return {}

		# If filters is a list of lists, convert to dict
		# LLM sometimes returns: [["field", "op", "value"], ...]
		if isinstance(filters, list):
			converted = {}
			for item in filters:
				if isinstance(item, list) and len(item) >= 3:
					field, op, value = item[0], item[1], item[2]
					converted[field] = [op, value]
				elif isinstance(item, list) and len(item) == 2:
					# Might be [op, value] without field - skip these
					continue
			filters = converted

		if not isinstance(filters, dict):
			return {}

		today = nowdate()

		# Date keyword replacements
		date_keywords = {
			"today": today,
			"now": today,
			"current_date": today,
			"yesterday": add_days(today, -1),
			"tomorrow": add_days(today, 1),
			"last_week": add_days(today, -7),
			"last_month": add_days(today, -30),
			"last_quarter": add_days(today, -90),
			"last_year": add_days(today, -365),
		}

		def replace_date_keywords(value):
			"""Recursively replace date keywords in filter values."""
			if isinstance(value, str):
				value_lower = value.lower().strip()
				if value_lower in date_keywords:
					return date_keywords[value_lower]
				return value
			elif isinstance(value, list):
				return [replace_date_keywords(v) for v in value]
			elif isinstance(value, dict):
				return {k: replace_date_keywords(v) for k, v in value.items()}
			return value

		sanitized = {}
		for key, value in filters.items():
			sanitized[key] = replace_date_keywords(value)

		return sanitized

	def _generate_ai_summary(self, question, doctype, results, query_params):
		"""
		Generate human-readable AI summary of query results.

		Args:
		    question: Original user question
		    doctype: DocType that was queried
		    results: Query results
		    query_params: LLM-generated query parameters

		Returns:
		    Human-readable summary string
		"""
		try:
			from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
				call_llm,
			)

			# If no results, generate analytical summary
			if not results:
				# For analytical questions, provide insights even with 0 results
				no_results_prompt = f"""The user asked: "{question}"

The AI attempted to find relevant {doctype} records but found 0 matches with these filters: {json.dumps(query_params.get('filters', {}))}

Provide a brief, helpful response (2-3 sentences) that:
1. Acknowledges that no directly matching records were found
2. Explains what this means in the context of their question
3. Suggests what they could check or consider instead

Be professional and helpful, not apologetic."""

				try:
					ai_response = call_llm(
						prompt=no_results_prompt,
						system_message="You are a compliance expert providing helpful guidance.",
					)
					summary = ai_response.strip().strip("\"'")
					if summary and len(summary) > 20:
						return summary
				except Exception:
					pass

				return _("No matching {0} found for your query").format(doctype)

			# Build summary of results for LLM context
			result_count = len(results)
			result_summary = []

			# Include up to 5 results with key fields
			for i, result in enumerate(results[:5]):
				result_str = f"{i+1}. "
				# Get the most relevant fields
				if "control_name" in result:
					result_str += f"{result.get('control_name', result.get('name'))} "
				elif "risk_name" in result:
					result_str += f"{result.get('risk_name', result.get('name'))} "
				else:
					result_str += f"{result.get('name')} "

				# Add relevant details
				if "status" in result:
					result_str += f"(Status: {result.get('status')}) "
				if "control_type" in result:
					result_str += f"(Type: {result.get('control_type')}) "
				if "residual_risk_score" in result:
					result_str += f"(Risk Score: {result.get('residual_risk_score')}) "

				result_summary.append(result_str.strip())

			result_text = "\n".join(result_summary)
			if result_count > 5:
				result_text += f"\n... and {result_count - 5} more"

			# Generate AI summary
			summary_prompt = f"""Based on the user's question and the query results, provide a concise, helpful summary (2-3 sentences maximum).

User Question: {question}

Query Results ({result_count} {doctype} found):
{result_text}

Filters Applied: {json.dumps(query_params.get('filters', {}))}

Provide a natural language summary that:
1. Directly answers the user's question
2. Highlights key findings from the results
3. Uses professional compliance/audit terminology
4. Is concise (2-3 sentences max)

Do not just say "Found X results" - provide insight about WHAT was found and WHY it matters."""

			ai_response = call_llm(
				prompt=summary_prompt,
				system_message="You are a compliance expert providing concise, insightful summaries of compliance data.",
			)

			# Clean up the response (remove quotes if LLM wrapped it)
			summary = ai_response.strip().strip("\"'")

			# Fallback if summary is too generic or empty
			if not summary or len(summary) < 20:
				return _("Found {0} {1} matching your criteria").format(result_count, doctype)

			return summary

		except Exception as e:
			frappe.log_error(
				message=f"AI Summary Generation Error: {str(e)}", title="NL Query AI Summary Error"
			)
			# Fallback to simple count message
			return _("Found {0} {1}").format(len(results), doctype)

	def _build_llm_context(self):
		"""Build context about available DocTypes for LLM."""
		doctypes = {
			"Control Activity": [
				"name",
				"control_name",
				"control_type",
				"status",
				"control_owner",
				"is_key_control",
				"automation_level",
				"frequency",
				"last_test_date",
				"next_test_date",
				"control_category",
			],
			"Risk Register Entry": [
				"name",
				"risk_name",
				"risk_category",
				"risk_owner",
				"status",
				"inherent_risk_score",
				"residual_risk_score",
			],
			"Deficiency": [
				"name",
				"description",
				"severity",
				"status",
				"control",
				"identified_date",
				"target_date",
			],
			"Test Execution": [
				"name",
				"control",
				"test_date",
				"test_result",
				"tester",
				"conclusion",
				"docstatus",
			],
			"Compliance Framework": ["name", "framework_name", "description", "status"],
			"Risk Prediction": [
				"name",
				"control",
				"control_name",
				"prediction_date",
				"failure_probability",
				"risk_level",
				"is_current",
				"contributing_factors",
				"recommended_actions",
			],
		}

		context_lines = []
		for doctype, fields in doctypes.items():
			context_lines.append(f"{doctype}: {', '.join(fields)}")

		return "\n".join(context_lines)

	def _log_query(self, question, parsed, result):
		"""Log the query for analytics and improvement."""
		try:
			# Convert result to JSON-serializable format by using frappe.as_json
			# which handles date/datetime objects properly
			response_data = None
			if result.get("results"):
				try:
					response_data = frappe.as_json(result)
				except Exception:
					# If serialization still fails, skip storing response data
					response_data = None

			log = frappe.get_doc(
				{
					"doctype": "NL Query Log",
					"question": question,
					"parsed_intent": json.dumps(parsed.get("intents", [])),
					"parsed_entities": json.dumps(parsed.get("entities", {})),
					"generated_query": json.dumps(
						{"doctype": parsed.get("doctype"), "filters": parsed.get("filters")}
					),
					"query_successful": result.get("success", False),
					"response": result.get("response"),
					"response_data": response_data,
					"result_count": result.get("count", 0),
				}
			)
			log.flags.ignore_permissions = True
			log.insert()
		except Exception as e:
			# Don't fail the query if logging fails
			frappe.log_error(message=f"Failed to log NL query: {str(e)}", title=_("NL Query Log Error"))

	def get_suggestions(self, partial_query):
		"""
		Get query suggestions based on partial input.

		Args:
		    partial_query: Partial query string

		Returns:
		    List of suggested queries
		"""
		suggestions = []
		partial_lower = partial_query.lower()

		# Common query templates
		templates = [
			"Show me all active controls",
			"Show me all high risk controls",
			"Which controls failed testing last month?",
			"What are the open deficiencies?",
			"List controls owned by {owner}",
			"How many tests were executed this quarter?",
			"Show me SOX controls",
			"What are the overdue tests?",
			"List critical risks",
			"Show me manual controls",
		]

		for template in templates:
			if partial_lower in template.lower():
				suggestions.append(template)

		return suggestions[:5]  # Return top 5


# API Endpoints
@frappe.whitelist()
def ask_compliance_question(question, use_llm=False):
	"""
	API endpoint to ask a compliance question.

	IMPORTANT: Rule-based queries (use_llm=False) work WITHOUT any AI configuration.
	Only AI-enhanced queries (use_llm=True) require "Enable AI-Enhanced NL Queries" setting.

	Args:
	    question: Natural language question
	    use_llm: Whether to use LLM (default False)

	Returns:
	    Query result
	"""
	use_llm = cint(use_llm)

	# CRITICAL: Only check AI feature flag when user explicitly requests AI-enhanced queries
	# Rule-based queries must work without any AI settings enabled
	if use_llm:
		try:
			from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
				is_ai_feature_enabled,
			)

			if not is_ai_feature_enabled("natural_language_queries"):
				frappe.throw(
					_(
						"AI-enhanced queries are not enabled. Please uncheck 'AI Enhanced' to use rule-based queries, "
						"or enable 'AI-Enhanced NL Queries' in AI Provider Settings."
					)
				)
		except Exception as e:
			frappe.log_error(message=f"Error checking AI feature: {str(e)}", title="NL Query AI Check Error")
			frappe.throw(
				_(
					"Could not verify AI configuration. Please uncheck 'AI Enhanced' to use rule-based queries."
				)
			)

	# Check permissions - user needs read access to at least one compliance DocType
	compliance_doctypes = ["Control Activity", "Risk Register Entry", "Deficiency", "Control Evidence"]
	has_any_permission = any(frappe.has_permission(dt, "read") for dt in compliance_doctypes)

	if not has_any_permission:
		frappe.throw(
			_(
				"You do not have permission to query compliance data. Please contact your system administrator."
			),
			frappe.PermissionError,
		)

	engine = NLQueryEngine()
	return engine.query(question, use_llm=use_llm)


@frappe.whitelist()
def get_query_suggestions(partial_query):
	"""
	API endpoint to get query suggestions.

	Args:
	    partial_query: Partial query string

	Returns:
	    List of suggestions
	"""
	# Permission check - user must have read access to at least one compliance DocType
	compliance_doctypes = ["Control Activity", "Risk Register Entry", "Deficiency", "Control Evidence"]
	has_any_permission = any(frappe.has_permission(dt, "read") for dt in compliance_doctypes)

	if not has_any_permission:
		frappe.throw(
			_(
				"You do not have permission to access compliance data. Please contact your system administrator."
			),
			frappe.PermissionError,
		)

	engine = NLQueryEngine()
	return engine.get_suggestions(partial_query)


@frappe.whitelist()
def parse_question(question):
	"""
	API endpoint to parse a question without executing.

	Args:
	    question: Natural language question

	Returns:
	    Parsed query structure
	"""
	# Permission check - user must have read access to at least one compliance DocType
	compliance_doctypes = ["Control Activity", "Risk Register Entry", "Deficiency", "Control Evidence"]
	has_any_permission = any(frappe.has_permission(dt, "read") for dt in compliance_doctypes)

	if not has_any_permission:
		frappe.throw(
			_(
				"You do not have permission to access compliance data. Please contact your system administrator."
			),
			frappe.PermissionError,
		)

	engine = NLQueryEngine()
	return engine.parse_question(question)
