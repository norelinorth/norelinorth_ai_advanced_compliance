# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class RegulatoryChange(Document):
	"""
	DocType for tracking specific changes detected in regulatory updates.

	Stores the old and new text, change analysis, and severity classification.
	"""

	def validate(self):
		"""Validate regulatory change."""
		self.auto_classify_severity()

	def auto_classify_severity(self):
		"""
		Auto-classify severity based on change characteristics.

		Updates severity if obligation changed or new requirements added.
		"""
		if self.obligation_changed or self.new_requirements:
			if self.severity in ("Minor", "Moderate"):
				self.severity = "Major"

		# Critical if semantic similarity is very low
		if self.semantic_similarity and flt(self.semantic_similarity) < 50:
			self.severity = "Critical"

	def analyze_change(self):
		"""
		Analyze the change using change detection algorithms.

		Calculates text and semantic similarity, detects obligation changes.
		"""
		if not self.old_text or not self.new_text:
			return

		from advanced_compliance.advanced_compliance.regulatory_feeds.detection.change_detector import (
			ChangeDetector,
			SemanticChangeDetector,
		)

		# Text similarity
		detector = ChangeDetector(self.old_text, self.new_text)
		self.text_similarity = flt(detector.calculate_similarity() * 100, 2)

		# Detect obligation changes
		self.obligation_changed = self._detect_obligation_change()

		# Semantic similarity (if available)
		try:
			semantic_detector = SemanticChangeDetector()
			result = semantic_detector.detect_meaning_changes(self.old_text, self.new_text)
			self.semantic_similarity = flt(result["semantic_similarity"] * 100, 2)
		except Exception:
			# Semantic analysis not available
			pass

		self.status = "Analyzed"
		self.save(ignore_permissions=True)

	def _detect_obligation_change(self):
		"""
		Detect if obligation level changed between versions.

		Looks for changes from optional to mandatory language.

		Returns:
			bool: True if obligation strengthened
		"""
		if not self.old_text or not self.new_text:
			return False

		old_lower = self.old_text.lower()
		new_lower = self.new_text.lower()

		# Optional → Mandatory indicators
		optional_words = ["may", "should", "can", "might", "could"]
		mandatory_words = ["must", "shall", "required", "mandatory", "will"]

		old_has_optional = any(w in old_lower for w in optional_words)
		new_has_mandatory = any(w in new_lower for w in mandatory_words)

		# Check if optional became mandatory
		if old_has_optional:
			for mandatory in mandatory_words:
				if mandatory in new_lower and mandatory not in old_lower:
					return True

		return False

	def extract_citations(self):
		"""
		Extract regulatory citations from change text.

		Returns:
			list: List of citation strings found
		"""
		from advanced_compliance.advanced_compliance.regulatory_feeds.parsers.document_parser import (
			DocumentParser,
		)

		text = f"{self.old_text or ''} {self.new_text or ''}"
		parser = DocumentParser(text)
		citations = parser.extract_citations()

		if citations:
			self.affected_citations = ", ".join(citations)
			self.save(ignore_permissions=True)

		return citations

	def create_impact_assessments(self, min_confidence=50.0):
		"""
		Create impact assessments for affected controls.

		Args:
			min_confidence: Minimum confidence threshold

		Returns:
			list: Names of created assessments
		"""
		from advanced_compliance.advanced_compliance.regulatory_feeds.mapping.impact_mapper import (
			ImpactMapper,
		)

		mapper = ImpactMapper(self)
		assessments = mapper.create_impact_assessments(min_confidence=min_confidence)

		if assessments:
			self.status = "Impact Assessed"
			self.save(ignore_permissions=True)

		return assessments
