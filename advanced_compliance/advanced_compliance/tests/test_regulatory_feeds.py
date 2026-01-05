# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Comprehensive Tests for Phase 5: Regulatory Feeds

Test Coverage:
- Regulatory Feed Source DocType
- Regulatory Update DocType
- Regulatory Change DocType
- Regulatory Impact Assessment DocType
- Connector Framework
- Document Parser
- Change Detection
- Impact Mapping
- Notifications
- API Endpoints
"""

import unittest
from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.utils import add_days, getdate, nowdate


class TestRegulatoryFeedSource(unittest.TestCase):
	"""Tests for Regulatory Feed Source DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test data once."""
		frappe.set_user("Administrator")

	def setUp(self):
		"""Set up before each test."""
		frappe.db.rollback()

	def tearDown(self):
		"""Clean up after each test."""
		frappe.db.rollback()

	def test_create_rss_feed_source(self):
		"""Test creating an RSS feed source."""
		doc = frappe.get_doc(
			{
				"doctype": "Regulatory Feed Source",
				"source_name": "Test SEC RSS Feed",
				"feed_type": "RSS",
				"url": "https://www.sec.gov/news/pressreleases.rss",
				"regulatory_body": "SEC",
				"enabled": 1,
				"sync_frequency": "Daily",
			}
		)
		doc.insert()

		self.assertEqual(doc.source_name, "Test SEC RSS Feed")
		self.assertEqual(doc.feed_type, "RSS")
		self.assertEqual(doc.regulatory_body, "SEC")

	def test_feed_source_url_validation(self):
		"""Test that invalid URLs are rejected."""
		doc = frappe.get_doc(
			{
				"doctype": "Regulatory Feed Source",
				"source_name": "Invalid URL Feed",
				"feed_type": "RSS",
				"url": "not-a-valid-url",
				"enabled": 1,
			}
		)

		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_sec_edgar_requires_user_agent(self):
		"""Test that SEC EDGAR feeds require user agent."""
		doc = frappe.get_doc(
			{
				"doctype": "Regulatory Feed Source",
				"source_name": "SEC EDGAR Feed",
				"feed_type": "SEC EDGAR",
				"url": "https://www.sec.gov/cgi-bin/browse-edgar",
				"user_agent": "",  # Empty user agent
			}
		)

		with self.assertRaises(frappe.ValidationError):
			doc.insert()


class TestRegulatoryUpdate(unittest.TestCase):
	"""Tests for Regulatory Update DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test data once."""
		frappe.set_user("Administrator")

	def setUp(self):
		"""Set up before each test."""
		frappe.db.rollback()

	def tearDown(self):
		"""Clean up after each test."""
		frappe.db.rollback()

	def test_create_regulatory_update(self):
		"""Test creating a regulatory update."""
		doc = frappe.get_doc(
			{
				"doctype": "Regulatory Update",
				"title": "SEC Final Rule on Climate Disclosure",
				"regulatory_body": "SEC",
				"document_type": "Rule",
				"publication_date": nowdate(),
				"effective_date": add_days(nowdate(), 90),
				"summary": "New climate disclosure requirements for public companies.",
			}
		)
		doc.insert()

		self.assertIsNotNone(doc.name)
		self.assertEqual(doc.status, "New")

	def test_days_until_effective_calculation(self):
		"""Test automatic calculation of days until effective."""
		effective_date = add_days(nowdate(), 30)

		doc = frappe.get_doc(
			{"doctype": "Regulatory Update", "title": "Test Update", "effective_date": effective_date}
		)
		doc.insert()

		self.assertEqual(doc.days_until_effective, 30)

	def test_unique_url_constraint(self):
		"""Test that original_url must be unique."""
		import time

		url = f"https://www.sec.gov/rules/final/2024/test-rule-{time.time()}.htm"

		doc1 = frappe.get_doc({"doctype": "Regulatory Update", "title": "First Update", "original_url": url})
		doc1.insert()

		doc2 = frappe.get_doc({"doctype": "Regulatory Update", "title": "Second Update", "original_url": url})

		with self.assertRaises((frappe.DuplicateEntryError, frappe.UniqueValidationError)):
			doc2.insert()


class TestRegulatoryChange(unittest.TestCase):
	"""Tests for Regulatory Change DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test data once."""
		frappe.set_user("Administrator")

	def setUp(self):
		"""Set up before each test."""
		frappe.db.rollback()
		# Create a regulatory update for each test
		self.update = frappe.get_doc(
			{"doctype": "Regulatory Update", "title": "Test Regulatory Update", "regulatory_body": "SEC"}
		)
		self.update.insert()

	def tearDown(self):
		"""Clean up after each test."""
		frappe.db.rollback()

	def test_create_regulatory_change(self):
		"""Test creating a regulatory change."""
		doc = frappe.get_doc(
			{
				"doctype": "Regulatory Change",
				"regulatory_update": self.update.name,
				"change_type": "Amendment",
				"severity": "Major",
				"summary_of_change": "Changed 'should' to 'must' in reporting requirements.",
			}
		)
		doc.insert()

		self.assertIsNotNone(doc.name)

	def test_auto_severity_upgrade(self):
		"""Test that severity is upgraded when obligation changes."""
		doc = frappe.get_doc(
			{
				"doctype": "Regulatory Change",
				"regulatory_update": self.update.name,
				"change_type": "Amendment",
				"severity": "Minor",
				"obligation_changed": 1,  # This should trigger upgrade
			}
		)
		doc.insert()

		self.assertEqual(doc.severity, "Major")


class TestRegulatoryImpactAssessment(unittest.TestCase):
	"""Tests for Regulatory Impact Assessment DocType."""

	@classmethod
	def setUpClass(cls):
		"""Set up test data once."""
		frappe.set_user("Administrator")

	def setUp(self):
		"""Set up before each test."""
		frappe.db.rollback()

		# Create prerequisite documents for each test
		self.update = frappe.get_doc(
			{"doctype": "Regulatory Update", "title": "Test Update for Impact", "regulatory_body": "SEC"}
		)
		self.update.insert()

		self.change = frappe.get_doc(
			{
				"doctype": "Regulatory Change",
				"regulatory_update": self.update.name,
				"change_type": "New Requirement",
				"severity": "Major",
			}
		)
		self.change.insert()

		# Create a control activity
		self.control = frappe.get_doc(
			{
				"doctype": "Control Activity",
				"control_name": "Test Control for Impact",
				"control_owner": "Administrator",
			}
		)
		self.control.insert()

	def tearDown(self):
		"""Clean up after each test."""
		frappe.db.rollback()

	def test_create_impact_assessment(self):
		"""Test creating an impact assessment."""
		doc = frappe.get_doc(
			{
				"doctype": "Regulatory Impact Assessment",
				"regulatory_change": self.change.name,
				"control_activity": self.control.name,
				"confidence_score": 85.0,
				"impact_type": "Review Required",
			}
		)
		doc.insert()

		self.assertIsNotNone(doc.name)
		self.assertEqual(doc.status, "Pending")

	def test_auto_set_priority(self):
		"""Test automatic priority setting based on severity."""
		doc = frappe.get_doc(
			{
				"doctype": "Regulatory Impact Assessment",
				"regulatory_change": self.change.name,
				"control_activity": self.control.name,
				"confidence_score": 90.0,
			}
		)
		doc.insert()

		# Change has "Major" severity, so priority should be "High"
		self.assertEqual(doc.priority, "High")


class TestDocumentParser(unittest.TestCase):
	"""Tests for Document Parser module."""

	def test_extract_cfr_citations(self):
		"""Test extraction of CFR citations."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.parsers.document_parser import (
			DocumentParser,
		)

		text = """
		This rule amends 17 CFR 240.10b-5 and 17 CFR Part 249.
		Additional requirements under 15 CFR 240.14a-8 apply.
		"""

		parser = DocumentParser(text)
		citations = parser.extract_citations()

		self.assertIn("17 CFR 240.10B-5", citations)
		self.assertIn("17 CFR PART 249", citations)

	def test_extract_asc_citations(self):
		"""Test extraction of ASC citations."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.parsers.document_parser import (
			DocumentParser,
		)

		text = """
		Companies must comply with ASC 606-10-25 for revenue recognition
		and ASC 842 for lease accounting.
		"""

		parser = DocumentParser(text)
		citations = parser.extract_citations()

		self.assertIn("ASC 606-10-25", citations)
		self.assertIn("ASC 842", citations)

	def test_extract_effective_date(self):
		"""Test extraction of effective dates."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.parsers.document_parser import (
			DocumentParser,
		)

		text = "This rule becomes effective January 1, 2025."

		parser = DocumentParser(text)
		effective_date = parser.extract_effective_date()

		self.assertIsNotNone(effective_date)
		self.assertEqual(effective_date.year, 2025)
		self.assertEqual(effective_date.month, 1)
		self.assertEqual(effective_date.day, 1)

	def test_extract_keywords(self):
		"""Test keyword extraction."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.parsers.document_parser import (
			DocumentParser,
		)

		text = """
		Revenue recognition requirements for software companies.
		Companies must recognize revenue when performance obligations
		are satisfied. Revenue recognition is critical for compliance.
		"""

		parser = DocumentParser(text)
		keywords = parser.extract_keywords(top_n=5)

		self.assertIsInstance(keywords, list)
		self.assertTrue(len(keywords) <= 5)

	def test_detect_obligation_level(self):
		"""Test obligation level detection."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.parsers.document_parser import (
			DocumentParser,
		)

		text = """
		Companies must file reports quarterly.
		They shall maintain adequate records.
		Organizations may choose optional disclosures.
		"""

		parser = DocumentParser(text)
		obligations = parser.detect_obligation_level()

		self.assertGreater(obligations["mandatory"], 0)
		self.assertGreater(obligations["permissive"], 0)


class TestChangeDetector(unittest.TestCase):
	"""Tests for Change Detection module."""

	def test_calculate_similarity(self):
		"""Test text similarity calculation."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.detection.change_detector import (
			ChangeDetector,
		)

		old_text = "Companies should file quarterly reports."
		new_text = "Companies must file quarterly reports."

		detector = ChangeDetector(old_text, new_text)
		similarity = detector.calculate_similarity()

		# Should be high similarity (one word change)
		self.assertGreater(similarity, 0.8)

	def test_detect_changes(self):
		"""Test change detection."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.detection.change_detector import (
			ChangeDetector,
		)

		old_text = "Line 1\nLine 2\nLine 3"
		new_text = "Line 1\nModified Line 2\nLine 3\nLine 4"

		detector = ChangeDetector(old_text, new_text)
		changes = detector.detect_changes()

		self.assertIsInstance(changes, list)
		self.assertTrue(len(changes) > 0)

	def test_classify_severity(self):
		"""Test severity classification."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.detection.change_detector import (
			ChangeDetector,
		)

		# Test major change (new mandatory requirement)
		old_text = "Companies may disclose."
		new_text = "Companies must disclose. Violations will result in penalties."

		detector = ChangeDetector(old_text, new_text)
		changes = detector.detect_changes()

		# Should detect as major or critical due to penalty keyword
		if changes:
			self.assertIn(changes[0]["severity"], ["Major", "Critical"])

	def test_detect_obligation_changes(self):
		"""Test obligation change detection."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.detection.change_detector import (
			ChangeDetector,
		)

		old_text = "Companies should maintain records."
		new_text = "Companies must maintain records."

		detector = ChangeDetector(old_text, new_text)
		obligation_changes = detector.detect_obligation_changes()

		self.assertTrue(len(obligation_changes) > 0)
		self.assertEqual(obligation_changes[0]["type"], "strengthened")


class TestImpactMapper(unittest.TestCase):
	"""Tests for Impact Mapping module."""

	@classmethod
	def setUpClass(cls):
		"""Set up test data once."""
		frappe.set_user("Administrator")

	def setUp(self):
		"""Set up before each test."""
		frappe.db.rollback()

		# Create regulatory change for each test
		self.update = frappe.get_doc(
			{"doctype": "Regulatory Update", "title": "Impact Test Update", "regulatory_body": "SEC"}
		)
		self.update.insert()

		self.change = frappe.get_doc(
			{
				"doctype": "Regulatory Change",
				"regulatory_update": self.update.name,
				"change_type": "Amendment",
				"severity": "Major",
				"summary_of_change": "New requirements for 17 CFR 240.10b-5 compliance.",
				"new_text": "Companies must comply with 17 CFR 240.10b-5.",
			}
		)
		self.change.insert()

		# Create control with matching citation
		self.control = frappe.get_doc(
			{
				"doctype": "Control Activity",
				"control_name": "SEC Rule 10b-5 Compliance Control",
				"description": "Control to ensure compliance with 17 CFR 240.10b-5",
				"control_owner": "Administrator",
			}
		)
		self.control.insert()

	def tearDown(self):
		"""Clean up after each test."""
		frappe.db.rollback()

	def test_find_affected_controls(self):
		"""Test finding affected controls."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.mapping.impact_mapper import (
			ImpactMapper,
		)

		mapper = ImpactMapper(self.change)
		affected = mapper.find_affected_controls()

		self.assertIsInstance(affected, list)
		# Should find our control due to citation match
		control_names = [m["control"] for m in affected]
		self.assertIn(self.control.name, control_names)

	def test_citation_matching_high_confidence(self):
		"""Test that citation matches have high confidence."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.mapping.impact_mapper import (
			ImpactMapper,
		)

		mapper = ImpactMapper(self.change)
		affected = mapper.find_affected_controls()

		# Find our control's match
		for match in affected:
			if match["control"] == self.control.name:
				self.assertGreaterEqual(match["confidence"], 80)
				self.assertEqual(match["method"], "citation")


class TestRegulatoryAPI(unittest.TestCase):
	"""Tests for API endpoints."""

	@classmethod
	def setUpClass(cls):
		"""Set up test data once."""
		frappe.set_user("Administrator")

	def setUp(self):
		"""Set up before each test."""
		frappe.db.rollback()

	def tearDown(self):
		"""Clean up after each test."""
		frappe.db.rollback()

	def test_get_regulatory_timeline(self):
		"""Test getting regulatory timeline."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.api import get_regulatory_timeline

		# Create update with future effective date
		doc = frappe.get_doc(
			{
				"doctype": "Regulatory Update",
				"title": "Timeline Test Update",
				"effective_date": add_days(nowdate(), 30),
				"status": "Pending Review",
			}
		)
		doc.insert()

		timeline = get_regulatory_timeline(days=60)

		self.assertIsInstance(timeline, list)
		# Should include our update
		titles = [u.title for u in timeline]
		self.assertIn("Timeline Test Update", titles)

	def test_get_feed_status(self):
		"""Test getting feed status."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.api import get_feed_status

		# Create a feed source
		doc = frappe.get_doc(
			{
				"doctype": "Regulatory Feed Source",
				"source_name": "Status Test Feed",
				"feed_type": "RSS",
				"url": "https://example.com/feed.rss",
				"enabled": 1,
			}
		)
		doc.insert()

		status = get_feed_status()

		self.assertIsInstance(status, list)
		# Should include our feed
		feed_names = [f["source_name"] for f in status]
		self.assertIn("Status Test Feed", feed_names)

	def test_get_compliance_dashboard_data(self):
		"""Test getting dashboard data."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.api import get_compliance_dashboard_data

		data = get_compliance_dashboard_data()

		self.assertIn("updates_by_status", data)
		self.assertIn("pending_assessments", data)
		self.assertIn("upcoming_deadlines", data)


class TestConnectorFactory(unittest.TestCase):
	"""Tests for connector factory."""

	def test_get_rss_connector(self):
		"""Test getting RSS connector."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.connectors import get_connector

		feed_source = frappe._dict(
			{
				"source_name": "Test RSS",
				"feed_type": "RSS",
				"url": "https://example.com/feed.rss",
				"last_sync": None,
				"user_agent": "Test/1.0",
				"document_types": "",
				"keywords": [],
			}
		)

		connector = get_connector(feed_source)

		from advanced_compliance.advanced_compliance.regulatory_feeds.connectors.rss_connector import (
			RSSConnector,
		)

		self.assertIsInstance(connector, RSSConnector)

	def test_get_sec_connector(self):
		"""Test getting SEC EDGAR connector."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.connectors import get_connector

		feed_source = frappe._dict(
			{
				"source_name": "Test SEC",
				"feed_type": "SEC EDGAR",
				"url": "https://www.sec.gov/feed",
				"last_sync": None,
				"user_agent": "Test/1.0",
				"document_types": "",
				"keywords": [],
			}
		)

		connector = get_connector(feed_source)

		from advanced_compliance.advanced_compliance.regulatory_feeds.connectors.sec_edgar import (
			SECEdgarConnector,
		)

		self.assertIsInstance(connector, SECEdgarConnector)

	def test_invalid_feed_type_raises_error(self):
		"""Test that invalid feed type raises error."""
		from advanced_compliance.advanced_compliance.regulatory_feeds.connectors import get_connector

		feed_source = frappe._dict(
			{"source_name": "Invalid Feed", "feed_type": "INVALID_TYPE", "url": "https://example.com"}
		)

		with self.assertRaises(frappe.ValidationError):
			get_connector(feed_source)


def run_tests():
	"""Run all Phase 5 tests."""
	loader = unittest.TestLoader()
	suite = unittest.TestSuite()

	# Add all test classes
	suite.addTests(loader.loadTestsFromTestCase(TestRegulatoryFeedSource))
	suite.addTests(loader.loadTestsFromTestCase(TestRegulatoryUpdate))
	suite.addTests(loader.loadTestsFromTestCase(TestRegulatoryChange))
	suite.addTests(loader.loadTestsFromTestCase(TestRegulatoryImpactAssessment))
	suite.addTests(loader.loadTestsFromTestCase(TestDocumentParser))
	suite.addTests(loader.loadTestsFromTestCase(TestChangeDetector))
	suite.addTests(loader.loadTestsFromTestCase(TestImpactMapper))
	suite.addTests(loader.loadTestsFromTestCase(TestRegulatoryAPI))
	suite.addTests(loader.loadTestsFromTestCase(TestConnectorFactory))

	runner = unittest.TextTestRunner(verbosity=2)
	runner.run(suite)


if __name__ == "__main__":
	run_tests()
