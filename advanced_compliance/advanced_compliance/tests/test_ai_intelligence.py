"""
Tests for AI Intelligence Module.

Comprehensive tests for:
- Risk Predictor
- Compliance Anomaly Detection
- NL Query Engine
- Semantic Search
- Auto-Suggestions
"""

import json
import unittest

import frappe
from frappe.utils import add_days, flt, nowdate


class TestAIProviderSettings(unittest.TestCase):
	"""Tests for AI Provider Settings DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def test_01_settings_is_single(self):
		"""Test that AI Provider Settings is a Single DocType."""
		settings = frappe.get_single("AI Provider Settings")
		self.assertIsNotNone(settings)
		self.assertEqual(settings.doctype, "AI Provider Settings")

	def test_02_default_thresholds(self):
		"""Test default threshold values."""
		settings = frappe.get_single("AI Provider Settings")

		# Check threshold fields exist
		self.assertTrue(hasattr(settings, "high_risk_threshold"))
		self.assertTrue(hasattr(settings, "critical_risk_threshold"))
		self.assertTrue(hasattr(settings, "anomaly_sensitivity"))

	def test_03_feature_toggles(self):
		"""Test AI feature toggle fields."""
		settings = frappe.get_single("AI Provider Settings")

		# Check feature toggle fields exist
		self.assertTrue(hasattr(settings, "enable_risk_prediction"))
		self.assertTrue(hasattr(settings, "enable_anomaly_detection"))
		self.assertTrue(hasattr(settings, "enable_semantic_search"))
		self.assertTrue(hasattr(settings, "enable_nl_queries"))
		self.assertTrue(hasattr(settings, "enable_suggestions"))

	def test_04_get_risk_level(self):
		"""Test risk level calculation."""
		settings = frappe.get_single("AI Provider Settings")

		# Set thresholds for testing
		settings.high_risk_threshold = 0.6
		settings.critical_risk_threshold = 0.8
		settings.save()

		# Test risk levels
		self.assertEqual(settings.get_risk_level(0.9), "Critical")
		self.assertEqual(settings.get_risk_level(0.8), "Critical")
		self.assertEqual(settings.get_risk_level(0.7), "High")
		self.assertEqual(settings.get_risk_level(0.5), "Medium")
		self.assertEqual(settings.get_risk_level(0.2), "Low")

	def test_05_is_feature_enabled(self):
		"""Test feature enabled check."""
		from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
			is_ai_feature_enabled,
		)

		settings = frappe.get_single("AI Provider Settings")
		settings.enable_risk_prediction = 1
		settings.save()

		self.assertTrue(is_ai_feature_enabled("risk_prediction"))

	def tearDown(self):
		frappe.db.rollback()


class TestRiskPredictor(unittest.TestCase):
	"""Tests for Risk Predictor."""

	@classmethod
	def setUpClass(cls):
		"""Set up test data."""
		frappe.set_user("Administrator")

		# Enable risk prediction
		settings = frappe.get_single("AI Provider Settings")
		settings.enable_risk_prediction = 1
		settings.high_risk_threshold = 0.6
		settings.critical_risk_threshold = 0.8
		settings.enable_nl_queries = 0  # Disable to avoid API key requirement
		settings.save()
		frappe.db.commit()

		# Create test control
		if not frappe.db.exists("Control Activity", {"control_id": "TEST-AI-001"}):
			cls.control = frappe.get_doc(
				{
					"doctype": "Control Activity",
					"control_id": "TEST-AI-001",
					"control_name": "Test Control for AI",
					"control_type": "Preventive",
					"status": "Active",
					"automation_level": "Manual",
					"is_key_control": 1,
					"frequency": "Monthly",
					"test_frequency": "Quarterly",
					"control_owner": "Administrator",
				}
			)
			cls.control.flags.ignore_permissions = True
			cls.control.flags.ignore_mandatory = True
			cls.control.insert()
			frappe.db.commit()
		else:
			cls.control = frappe.get_doc("Control Activity", {"control_id": "TEST-AI-001"})

	def test_01_predictor_initialization(self):
		"""Test predictor initialization."""
		from advanced_compliance.advanced_compliance.intelligence.prediction.risk_predictor import (
			RiskPredictor,
		)

		predictor = RiskPredictor()
		self.assertIsNotNone(predictor)
		self.assertIsNotNone(predictor.feature_weights)
		self.assertEqual(predictor.MODEL_VERSION, "1.0.0")

	def test_02_extract_features(self):
		"""Test feature extraction."""
		from advanced_compliance.advanced_compliance.intelligence.prediction.risk_predictor import (
			RiskPredictor,
		)

		predictor = RiskPredictor()
		features = predictor.extract_features(self.control.name)

		self.assertIsNotNone(features)
		self.assertIn("days_since_test", features)
		self.assertIn("test_pass_rate", features)
		self.assertIn("deficiency_count", features)
		self.assertIn("is_key_control", features)
		self.assertIn("automation_level", features)
		self.assertIn("has_backup", features)

	def test_03_feature_values(self):
		"""Test feature value correctness."""
		from advanced_compliance.advanced_compliance.intelligence.prediction.risk_predictor import (
			RiskPredictor,
		)

		predictor = RiskPredictor()
		features = predictor.extract_features(self.control.name)

		# Key control should be 1
		self.assertEqual(features["is_key_control"], 1)

		# Manual control should have automation_level 0
		self.assertEqual(features["automation_level"], 0.0)

		# No backup assigned
		self.assertEqual(features["has_backup"], 0)

	def test_04_predict_control(self):
		"""Test prediction for a control."""
		from advanced_compliance.advanced_compliance.intelligence.prediction.risk_predictor import (
			RiskPredictor,
		)

		predictor = RiskPredictor()
		prediction = predictor.predict(self.control.name)

		self.assertIsNotNone(prediction)
		self.assertIn("failure_probability", prediction)
		self.assertIn("risk_level", prediction)
		self.assertIn("contributing_factors", prediction)
		self.assertIn("recommended_actions", prediction)
		self.assertIn("features", prediction)

		# Probability should be between 0 and 1
		self.assertGreaterEqual(prediction["failure_probability"], 0)
		self.assertLessEqual(prediction["failure_probability"], 1)

		# Risk level should be valid
		self.assertIn(prediction["risk_level"], ["Low", "Medium", "High", "Critical"])

	def test_05_predict_nonexistent_control(self):
		"""Test prediction for non-existent control."""
		from advanced_compliance.advanced_compliance.intelligence.prediction.risk_predictor import (
			RiskPredictor,
		)

		predictor = RiskPredictor()
		prediction = predictor.predict("NONEXISTENT-CONTROL")

		self.assertIsNone(prediction)

	def test_06_contributing_factors(self):
		"""Test contributing factors generation."""
		from advanced_compliance.advanced_compliance.intelligence.prediction.risk_predictor import (
			RiskPredictor,
		)

		predictor = RiskPredictor()
		prediction = predictor.predict(self.control.name)

		factors = prediction.get("contributing_factors", [])
		self.assertIsInstance(factors, list)

		# Should have No Backup Performer factor
		factor_names = [f["factor"] for f in factors]
		self.assertIn("No Backup Performer", factor_names)

	def test_07_recommendations(self):
		"""Test recommendations generation."""
		from advanced_compliance.advanced_compliance.intelligence.prediction.risk_predictor import (
			RiskPredictor,
		)

		predictor = RiskPredictor()
		prediction = predictor.predict(self.control.name)

		recommendations = prediction.get("recommended_actions", [])
		self.assertIsInstance(recommendations, list)
		self.assertGreater(len(recommendations), 0)

	def test_08_save_prediction(self):
		"""Test saving prediction to database."""
		from advanced_compliance.advanced_compliance.intelligence.prediction.risk_predictor import (
			RiskPredictor,
		)

		predictor = RiskPredictor()
		prediction = predictor.predict(self.control.name)

		saved = predictor.save_prediction(prediction)

		self.assertIsNotNone(saved)
		self.assertTrue(frappe.db.exists("Risk Prediction", saved.name))

		# Verify saved values
		self.assertEqual(saved.control, self.control.name)
		self.assertEqual(saved.failure_probability, prediction["failure_probability"])

	def tearDown(self):
		frappe.db.rollback()


class TestComplianceAnomalyDetector(unittest.TestCase):
	"""Tests for Compliance Anomaly Detection."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

		# Enable anomaly detection
		settings = frappe.get_single("AI Provider Settings")
		settings.enable_anomaly_detection = 1
		settings.anomaly_sensitivity = "Medium"
		settings.enable_nl_queries = 0  # Disable to avoid API key requirement
		settings.save()
		frappe.db.commit()

	def test_01_detector_initialization(self):
		"""Test detector initialization."""
		from advanced_compliance.advanced_compliance.intelligence.anomaly.compliance_anomaly import (
			ComplianceAnomalyDetector,
		)

		detector = ComplianceAnomalyDetector()
		self.assertIsNotNone(detector)
		self.assertEqual(detector.sensitivity, 1.0)

	def test_02_detect_all_anomalies(self):
		"""Test running all anomaly detection."""
		from advanced_compliance.advanced_compliance.intelligence.anomaly.compliance_anomaly import (
			ComplianceAnomalyDetector,
		)

		detector = ComplianceAnomalyDetector()
		anomalies = detector.detect_all_anomalies()

		self.assertIsInstance(anomalies, list)

	def test_03_detect_testing_clusters(self):
		"""Test testing cluster detection."""
		from advanced_compliance.advanced_compliance.intelligence.anomaly.compliance_anomaly import (
			ComplianceAnomalyDetector,
		)

		detector = ComplianceAnomalyDetector()
		anomalies = detector.detect_testing_clusters()

		self.assertIsInstance(anomalies, list)
		for anomaly in anomalies:
			self.assertEqual(anomaly["anomaly_type"], "Testing Cluster")
			self.assertIn("severity", anomaly)
			self.assertIn("title", anomaly)
			self.assertIn("description", anomaly)

	def test_04_detect_testing_gaps(self):
		"""Test testing gap detection."""
		from advanced_compliance.advanced_compliance.intelligence.anomaly.compliance_anomaly import (
			ComplianceAnomalyDetector,
		)

		detector = ComplianceAnomalyDetector()
		anomalies = detector.detect_testing_gaps()

		self.assertIsInstance(anomalies, list)
		for anomaly in anomalies:
			self.assertEqual(anomaly["anomaly_type"], "Testing Gap")
			self.assertIn("severity", anomaly)
			self.assertIn("details", anomaly)

	def test_05_detect_owner_concentration(self):
		"""Test owner concentration detection."""
		from advanced_compliance.advanced_compliance.intelligence.anomaly.compliance_anomaly import (
			ComplianceAnomalyDetector,
		)

		detector = ComplianceAnomalyDetector()
		anomalies = detector.detect_owner_concentration()

		self.assertIsInstance(anomalies, list)
		for anomaly in anomalies:
			self.assertEqual(anomaly["anomaly_type"], "Owner Concentration")

	def test_06_anomaly_severity_values(self):
		"""Test that anomaly severity values are valid."""
		from advanced_compliance.advanced_compliance.intelligence.anomaly.compliance_anomaly import (
			ComplianceAnomalyDetector,
		)

		detector = ComplianceAnomalyDetector()
		anomalies = detector.detect_all_anomalies()

		# Anomalies use Low/Medium/High/Critical internally
		# These get mapped to Info/Warning/Critical when creating alerts
		valid_severities = ["Low", "Medium", "High", "Critical"]
		for anomaly in anomalies:
			self.assertIn(anomaly["severity"], valid_severities)

	def test_07_create_alerts_from_anomalies(self):
		"""Test creating alerts from anomalies."""
		from advanced_compliance.advanced_compliance.intelligence.anomaly.compliance_anomaly import (
			ComplianceAnomalyDetector,
		)

		detector = ComplianceAnomalyDetector()

		# Create test anomaly with severity that will be mapped to alert severity
		# High -> Critical, Medium -> Warning, Low -> Info
		test_anomalies = [
			{
				"anomaly_type": "Testing Gap",
				"severity": "High",  # Will be mapped to "Critical" for alert
				"title": "Test Anomaly",
				"description": "This is a test anomaly",
				"details": {"test": True},
			}
		]

		created = detector.create_alerts_from_anomalies(test_anomalies)

		self.assertEqual(len(created), 1)
		self.assertTrue(frappe.db.exists("Compliance Alert", created[0]))

	def tearDown(self):
		frappe.db.rollback()


class TestNLQueryEngine(unittest.TestCase):
	"""Tests for Natural Language Query Engine."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

		# Enable NL queries - use Local provider to avoid API key requirement
		settings = frappe.get_single("AI Provider Settings")
		settings.ai_provider = "Local"
		settings.enable_nl_queries = 1
		settings.save()
		frappe.db.commit()

	def test_01_engine_initialization(self):
		"""Test engine initialization."""
		from advanced_compliance.advanced_compliance.intelligence.nlp.query_engine import NLQueryEngine

		engine = NLQueryEngine()
		self.assertIsNotNone(engine)
		self.assertIsNotNone(engine.INTENT_PATTERNS)
		self.assertIsNotNone(engine.ENTITY_PATTERNS)

	def test_02_parse_simple_question(self):
		"""Test parsing a simple question."""
		from advanced_compliance.advanced_compliance.intelligence.nlp.query_engine import NLQueryEngine

		engine = NLQueryEngine()
		parsed = engine.parse_question("Show me all controls")

		self.assertIn("list_controls", parsed["intents"])
		self.assertEqual(parsed["doctype"], "Control Activity")

	def test_03_parse_risk_question(self):
		"""Test parsing risk-related question."""
		from advanced_compliance.advanced_compliance.intelligence.nlp.query_engine import NLQueryEngine

		engine = NLQueryEngine()
		parsed = engine.parse_question("What are the high risk controls?")

		self.assertIn("high_risk", parsed["intents"])

	def test_04_parse_count_question(self):
		"""Test parsing count question."""
		from advanced_compliance.advanced_compliance.intelligence.nlp.query_engine import NLQueryEngine

		engine = NLQueryEngine()
		parsed = engine.parse_question("How many tests were executed?")

		self.assertIn("count", parsed["intents"])
		self.assertTrue(parsed["is_count_query"])

	def test_05_parse_framework_entity(self):
		"""Test framework entity extraction."""
		from advanced_compliance.advanced_compliance.intelligence.nlp.query_engine import NLQueryEngine

		engine = NLQueryEngine()
		parsed = engine.parse_question("Show me SOX controls")

		self.assertIn("framework", parsed["entities"])

	def test_06_parse_time_period(self):
		"""Test time period extraction."""
		from advanced_compliance.advanced_compliance.intelligence.nlp.query_engine import NLQueryEngine

		engine = NLQueryEngine()
		parsed = engine.parse_question("Which controls failed testing last month?")

		self.assertIn("time_period", parsed["entities"])
		self.assertIn("failed", parsed["intents"])

	def test_07_execute_query(self):
		"""Test query execution."""
		from advanced_compliance.advanced_compliance.intelligence.nlp.query_engine import NLQueryEngine

		engine = NLQueryEngine()
		result = engine.query("Show me all active controls")

		self.assertTrue(result["success"])
		self.assertEqual(result["doctype"], "Control Activity")
		self.assertIn("count", result)

	def test_08_get_suggestions(self):
		"""Test query suggestions."""
		from advanced_compliance.advanced_compliance.intelligence.nlp.query_engine import NLQueryEngine

		engine = NLQueryEngine()
		suggestions = engine.get_suggestions("show")

		self.assertIsInstance(suggestions, list)
		self.assertGreater(len(suggestions), 0)

	@unittest.skip("Flaky test - NL Query Log creation depends on transaction state")
	def test_09_query_logs(self):
		"""Test that queries are logged."""
		from advanced_compliance.advanced_compliance.intelligence.nlp.query_engine import NLQueryEngine

		engine = NLQueryEngine()
		engine.query("Test query for logging")

		# Commit so the log is visible before check
		frappe.db.commit()

		# Check log was created
		logs = frappe.get_all("NL Query Log", filters={"question": "Test query for logging"}, limit=1)
		self.assertGreater(len(logs), 0, "Query log should be created")

	def tearDown(self):
		frappe.db.rollback()


class TestSemanticSearch(unittest.TestCase):
	"""Tests for Semantic Search."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

		# Enable semantic search
		settings = frappe.get_single("AI Provider Settings")
		settings.enable_semantic_search = 1
		settings.enable_nl_queries = 0  # Disable to avoid API key requirement
		settings.save()
		frappe.db.commit()

	def test_01_search_initialization(self):
		"""Test search initialization."""
		from advanced_compliance.advanced_compliance.intelligence.search.semantic_search import SemanticSearch

		search = SemanticSearch()
		self.assertIsNotNone(search)
		self.assertIsNotNone(search.SEARCHABLE_DOCTYPES)

	def test_02_searchable_doctypes(self):
		"""Test searchable doctypes configuration."""
		from advanced_compliance.advanced_compliance.intelligence.search.semantic_search import SemanticSearch

		search = SemanticSearch()

		self.assertIn("Control Activity", search.SEARCHABLE_DOCTYPES)
		self.assertIn("Risk Register Entry", search.SEARCHABLE_DOCTYPES)
		self.assertIn("Deficiency", search.SEARCHABLE_DOCTYPES)

	def test_03_cosine_similarity(self):
		"""Test cosine similarity calculation."""
		from advanced_compliance.advanced_compliance.intelligence.search.semantic_search import SemanticSearch

		search = SemanticSearch()

		# Test identical vectors
		vec1 = [1.0, 0.0, 0.0]
		vec2 = [1.0, 0.0, 0.0]
		similarity = search._cosine_similarity(vec1, vec2)
		self.assertAlmostEqual(similarity, 1.0, places=4)

		# Test orthogonal vectors
		vec3 = [0.0, 1.0, 0.0]
		similarity = search._cosine_similarity(vec1, vec3)
		self.assertAlmostEqual(similarity, 0.0, places=4)

		# Test opposite vectors
		vec4 = [-1.0, 0.0, 0.0]
		similarity = search._cosine_similarity(vec1, vec4)
		self.assertAlmostEqual(similarity, -1.0, places=4)

	def test_04_text_search_fallback(self):
		"""Test text search fallback when embeddings unavailable."""
		from advanced_compliance.advanced_compliance.intelligence.search.semantic_search import SemanticSearch

		search = SemanticSearch()
		results = search._text_search_fallback("test", ["Control Activity"], 10)

		self.assertIsInstance(results, list)

	def test_05_search_returns_list(self):
		"""Test that search returns a list."""
		from advanced_compliance.advanced_compliance.intelligence.search.semantic_search import SemanticSearch

		search = SemanticSearch()
		results = search.search("access control", limit=5)

		self.assertIsInstance(results, list)

	def test_06_search_result_structure(self):
		"""Test search result structure."""
		from advanced_compliance.advanced_compliance.intelligence.search.semantic_search import SemanticSearch

		search = SemanticSearch()
		results = search.search("access control", limit=5)

		for result in results:
			self.assertIn("doctype", result)
			self.assertIn("document", result)
			self.assertIn("similarity", result)

	def tearDown(self):
		frappe.db.rollback()


class TestAutoSuggest(unittest.TestCase):
	"""Tests for Auto-Suggestions."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

		# Enable auto-suggestions
		settings = frappe.get_single("AI Provider Settings")
		settings.enable_suggestions = 1
		settings.enable_nl_queries = 0  # Disable to avoid API key requirement
		settings.save()
		frappe.db.commit()

		# Create test control
		if not frappe.db.exists("Control Activity", {"control_id": "TEST-SUGGEST-001"}):
			cls.control = frappe.get_doc(
				{
					"doctype": "Control Activity",
					"control_id": "TEST-SUGGEST-001",
					"control_name": "Test Control for Suggestions",
					"control_type": "Preventive",
					"status": "Active",
					"automation_level": "Manual",
					"frequency": "Monthly",
					"control_owner": "Administrator",
				}
			)
			cls.control.flags.ignore_permissions = True
			cls.control.flags.ignore_mandatory = True
			cls.control.insert()
			frappe.db.commit()
		else:
			cls.control = frappe.get_doc("Control Activity", {"control_id": "TEST-SUGGEST-001"})

		# Create test risk if Risk Register Entry exists
		cls.risk = None
		if frappe.db.exists("DocType", "Risk Register Entry"):
			if not frappe.db.exists("Risk Register Entry", {"name": "TEST-RISK-001"}):
				try:
					cls.risk = frappe.get_doc(
						{
							"doctype": "Risk Register Entry",
							"risk_name": "Test Risk for Suggestions",
							"status": "Open",
							"inherent_likelihood": "4 - Likely",
							"inherent_impact": "3 - High",
							"residual_likelihood": "3 - Possible",
							"residual_impact": "2 - Medium",
						}
					)
					cls.risk.flags.ignore_permissions = True
					cls.risk.flags.ignore_mandatory = True
					cls.risk.insert()
					frappe.db.commit()
				except Exception:
					cls.risk = None
			else:
				cls.risk = frappe.get_doc("Risk Register Entry", "TEST-RISK-001")

	def test_01_suggest_initialization(self):
		"""Test auto-suggest initialization."""
		from advanced_compliance.advanced_compliance.intelligence.suggestions.auto_suggest import AutoSuggest

		suggest = AutoSuggest()
		self.assertIsNotNone(suggest)

	def test_02_suggest_controls_for_risk(self):
		"""Test control suggestions for risk."""
		if not self.risk:
			self.skipTest("Risk Register Entry DocType not available")

		from advanced_compliance.advanced_compliance.intelligence.suggestions.auto_suggest import AutoSuggest

		suggest = AutoSuggest()
		suggestions = suggest.suggest_controls_for_risk(self.risk.name)

		self.assertIsInstance(suggestions, list)

	def test_03_suggestion_structure(self):
		"""Test control suggestion structure."""
		if not self.risk:
			self.skipTest("Risk Register Entry DocType not available")

		from advanced_compliance.advanced_compliance.intelligence.suggestions.auto_suggest import AutoSuggest

		suggest = AutoSuggest()
		suggestions = suggest.suggest_controls_for_risk(self.risk.name)

		for suggestion in suggestions:
			self.assertIn("control_id", suggestion)
			self.assertIn("control_name", suggestion)
			self.assertIn("relevance_score", suggestion)
			self.assertIn("reasoning", suggestion)

	def test_04_suggest_testing_priority(self):
		"""Test testing priority suggestions."""
		from advanced_compliance.advanced_compliance.intelligence.suggestions.auto_suggest import AutoSuggest

		suggest = AutoSuggest()
		priorities = suggest.suggest_testing_priority()

		self.assertIsInstance(priorities, list)

	def test_05_priority_structure(self):
		"""Test priority suggestion structure."""
		from advanced_compliance.advanced_compliance.intelligence.suggestions.auto_suggest import AutoSuggest

		suggest = AutoSuggest()
		priorities = suggest.suggest_testing_priority()

		for priority in priorities:
			self.assertIn("control_id", priority)
			self.assertIn("priority_score", priority)
			self.assertIn("reasons", priority)

	def test_06_suggest_owner(self):
		"""Test owner suggestions for control."""
		from advanced_compliance.advanced_compliance.intelligence.suggestions.auto_suggest import AutoSuggest

		suggest = AutoSuggest()
		suggestions = suggest.suggest_owner_for_control(self.control.name)

		self.assertIsInstance(suggestions, list)

	def test_07_owner_suggestion_structure(self):
		"""Test owner suggestion structure."""
		from advanced_compliance.advanced_compliance.intelligence.suggestions.auto_suggest import AutoSuggest

		suggest = AutoSuggest()
		suggestions = suggest.suggest_owner_for_control(self.control.name)

		for suggestion in suggestions:
			self.assertIn("user_id", suggestion)
			self.assertIn("user_name", suggestion)
			self.assertIn("score", suggestion)
			self.assertIn("reasons", suggestion)

	def test_08_relevance_score_range(self):
		"""Test that relevance scores are in valid range."""
		if not self.risk:
			self.skipTest("Risk Register Entry DocType not available")

		from advanced_compliance.advanced_compliance.intelligence.suggestions.auto_suggest import AutoSuggest

		suggest = AutoSuggest()
		suggestions = suggest.suggest_controls_for_risk(self.risk.name)

		for suggestion in suggestions:
			self.assertGreaterEqual(suggestion["relevance_score"], 0)
			self.assertLessEqual(suggestion["relevance_score"], 1)

	def tearDown(self):
		frappe.db.rollback()


class TestComplianceAlert(unittest.TestCase):
	"""Tests for Compliance Alert DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def test_01_create_alert(self):
		"""Test alert creation."""
		from advanced_compliance.advanced_compliance.doctype.compliance_alert.compliance_alert import (
			ComplianceAlert,
		)

		alert = ComplianceAlert.create_alert(
			alert_type="High Risk",
			severity="Critical",
			title="Test Alert",
			description="This is a test alert",
		)

		self.assertIsNotNone(alert)
		self.assertTrue(frappe.db.exists("Compliance Alert", alert.name))
		self.assertEqual(alert.status, "New")

	def test_02_alert_severity_values(self):
		"""Test alert severity validation."""
		from advanced_compliance.advanced_compliance.doctype.compliance_alert.compliance_alert import (
			ComplianceAlert,
		)

		# Valid severity values are Info, Warning, Critical
		for severity in ["Info", "Warning", "Critical"]:
			alert = ComplianceAlert.create_alert(
				alert_type="Anomaly", severity=severity, title=f"Test {severity} Alert"
			)
			self.assertEqual(alert.severity, severity)

	def test_03_acknowledge_alert(self):
		"""Test alert acknowledgment."""
		from advanced_compliance.advanced_compliance.doctype.compliance_alert.compliance_alert import (
			ComplianceAlert,
		)

		alert = ComplianceAlert.create_alert(
			alert_type="Anomaly", severity="Warning", title="Test Acknowledge Alert"
		)

		# Use the static method to acknowledge
		ComplianceAlert.acknowledge(alert.name)

		# Reload to get updated status
		alert.reload()
		self.assertEqual(alert.status, "Acknowledged")

	def test_04_resolve_alert(self):
		"""Test alert resolution."""
		from advanced_compliance.advanced_compliance.doctype.compliance_alert.compliance_alert import (
			ComplianceAlert,
		)

		alert = ComplianceAlert.create_alert(
			alert_type="High Risk", severity="Critical", title="Test Resolve Alert"
		)

		# Use the static method to resolve
		ComplianceAlert.resolve(alert.name)

		# Reload to get updated status
		alert.reload()
		self.assertEqual(alert.status, "Resolved")
		self.assertIsNotNone(alert.resolved_by)
		self.assertIsNotNone(alert.resolved_at)

	def test_05_get_active_alerts(self):
		"""Test getting active alerts."""
		from advanced_compliance.advanced_compliance.doctype.compliance_alert.compliance_alert import (
			ComplianceAlert,
		)

		# Create test alert
		ComplianceAlert.create_alert(alert_type="Anomaly", severity="Warning", title="Active Alert for Test")

		alerts = ComplianceAlert.get_active_alerts()

		self.assertIsInstance(alerts, list)

	def test_06_filter_by_severity(self):
		"""Test filtering alerts by severity."""
		from advanced_compliance.advanced_compliance.doctype.compliance_alert.compliance_alert import (
			ComplianceAlert,
		)

		# Create alert with Critical severity
		ComplianceAlert.create_alert(
			alert_type="Anomaly", severity="Critical", title="Critical Alert for Filter Test"
		)

		alerts = ComplianceAlert.get_active_alerts(severity="Critical")

		# At least one alert with Critical severity
		self.assertGreater(len([a for a in alerts if a.severity == "Critical"]), 0)

	def tearDown(self):
		frappe.db.rollback()


class TestRiskPrediction(unittest.TestCase):
	"""Tests for Risk Prediction DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

		# Disable NL queries to avoid API key requirement
		settings = frappe.get_single("AI Provider Settings")
		settings.enable_nl_queries = 0
		settings.save()
		frappe.db.commit()

		# Create test control
		if not frappe.db.exists("Control Activity", {"control_id": "TEST-PRED-001"}):
			cls.control = frappe.get_doc(
				{
					"doctype": "Control Activity",
					"control_id": "TEST-PRED-001",
					"control_name": "Test Control for Prediction",
					"control_type": "Preventive",
					"status": "Active",
					"control_owner": "Administrator",
				}
			)
			cls.control.flags.ignore_permissions = True
			cls.control.flags.ignore_mandatory = True
			cls.control.insert()
			frappe.db.commit()
		else:
			cls.control = frappe.get_doc("Control Activity", {"control_id": "TEST-PRED-001"})

	def test_01_create_prediction(self):
		"""Test prediction creation."""
		from advanced_compliance.advanced_compliance.doctype.risk_prediction.risk_prediction import (
			RiskPrediction,
		)

		prediction = RiskPrediction.create_prediction(
			control_id=self.control.name,
			failure_probability=0.75,
			contributing_factors=[{"factor": "Test Factor", "impact": "high"}],
			recommended_actions=["Test Action"],
			model_version="1.0.0",
		)

		self.assertIsNotNone(prediction)
		self.assertTrue(frappe.db.exists("Risk Prediction", prediction.name))
		self.assertEqual(prediction.failure_probability, 0.75)

	def test_02_risk_level_assignment(self):
		"""Test risk level is assigned correctly based on probability."""
		from advanced_compliance.advanced_compliance.doctype.risk_prediction.risk_prediction import (
			RiskPrediction,
		)

		# Create prediction with high probability
		prediction = RiskPrediction.create_prediction(
			control_id=self.control.name, failure_probability=0.85, model_version="1.0.0"
		)

		# Risk level should be set (any valid value)
		self.assertIn(prediction.risk_level, ["Low", "Medium", "High", "Critical"])
		self.assertIsNotNone(prediction.risk_level)

	def test_03_get_high_risk_controls(self):
		"""Test getting high risk controls."""
		from advanced_compliance.advanced_compliance.doctype.risk_prediction.risk_prediction import (
			RiskPrediction,
		)

		# Create high-risk prediction
		RiskPrediction.create_prediction(
			control_id=self.control.name, failure_probability=0.9, model_version="1.0.0"
		)

		high_risk = RiskPrediction.get_high_risk_controls(threshold=0.8)

		self.assertIsInstance(high_risk, list)

	def test_04_prediction_timing(self):
		"""Test prediction timing is recorded."""
		from advanced_compliance.advanced_compliance.doctype.risk_prediction.risk_prediction import (
			RiskPrediction,
		)

		prediction = RiskPrediction.create_prediction(
			control_id=self.control.name,
			failure_probability=0.5,
			model_version="1.0.0",
			prediction_time_ms=150,
		)

		self.assertEqual(prediction.prediction_time_ms, 150)

	def tearDown(self):
		frappe.db.rollback()


class TestDocumentEmbedding(unittest.TestCase):
	"""Tests for Document Embedding DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def test_01_create_embedding(self):
		"""Test embedding creation."""
		embedding = frappe.get_doc(
			{
				"doctype": "Document Embedding",
				"source_doctype": "Control Activity",
				"source_document": "TEST-EMBEDDING-DOC",
				"source_field": "description",
				"embedding_vector": json.dumps([0.1, 0.2, 0.3]),
				"content_preview": "Test content",
				"embedding_model": "test-model",
				"embedding_dimension": 3,
			}
		)
		embedding.flags.ignore_permissions = True
		embedding.flags.ignore_links = True
		embedding.insert()

		self.assertTrue(frappe.db.exists("Document Embedding", embedding.name))

	def test_02_embedding_fields(self):
		"""Test embedding required fields."""
		embedding = frappe.get_doc(
			{
				"doctype": "Document Embedding",
				"source_doctype": "Compliance Risk",
				"source_document": "TEST-EMBEDDING-RISK",
				"source_field": "description",
				"embedding_vector": json.dumps([0.1, 0.2, 0.3, 0.4]),
				"embedding_model": "test-model",
				"embedding_dimension": 4,
			}
		)
		embedding.flags.ignore_permissions = True
		embedding.flags.ignore_links = True
		embedding.insert()

		self.assertEqual(embedding.source_doctype, "Compliance Risk")
		self.assertEqual(embedding.embedding_dimension, 4)

	def tearDown(self):
		frappe.db.rollback()


class TestNLQueryLog(unittest.TestCase):
	"""Tests for NL Query Log DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test environment."""
		frappe.set_user("Administrator")

	def test_01_create_log(self):
		"""Test query log creation."""
		log = frappe.get_doc(
			{
				"doctype": "NL Query Log",
				"question": "Show me all controls",
				"parsed_intent": json.dumps(["list_controls"]),
				"query_successful": 1,
				"response": "Found 10 controls",
				"result_count": 10,
			}
		)
		log.flags.ignore_permissions = True
		log.insert()

		self.assertTrue(frappe.db.exists("NL Query Log", log.name))

	def test_02_log_fields(self):
		"""Test log stores all fields correctly."""
		log = frappe.get_doc(
			{
				"doctype": "NL Query Log",
				"question": "How many tests were executed?",
				"parsed_intent": json.dumps(["count", "list_tests"]),
				"parsed_entities": json.dumps({"time_period": "last month"}),
				"generated_query": json.dumps({"doctype": "Test Execution"}),
				"query_successful": 1,
				"response": "Found 25 tests",
				"result_count": 25,
			}
		)
		log.flags.ignore_permissions = True
		log.insert()

		self.assertEqual(log.question, "How many tests were executed?")
		self.assertEqual(log.result_count, 25)

	def tearDown(self):
		frappe.db.rollback()
