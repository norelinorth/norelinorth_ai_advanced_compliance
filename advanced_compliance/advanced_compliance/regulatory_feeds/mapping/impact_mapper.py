# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Impact Mapper

Maps regulatory changes to affected Control Activities using
multiple matching strategies: citation, keyword, and semantic.
"""

import frappe
from frappe import _
from frappe.utils import flt


class ImpactMapper:
	"""
	Map regulatory changes to affected controls.

	Uses three matching strategies:
	1. Citation matching - direct regulatory references
	2. Keyword matching - TF-IDF text overlap
	3. Semantic matching - AI-based meaning similarity
	"""

	def __init__(self, regulatory_change):
		"""
		Initialize with regulatory change.

		Args:
			regulatory_change: Regulatory Change document or name
		"""
		if isinstance(regulatory_change, str):
			regulatory_change = frappe.get_doc("Regulatory Change", regulatory_change)

		self.change = regulatory_change
		self.update = None

		if regulatory_change.regulatory_update:
			self.update = frappe.get_doc("Regulatory Update", regulatory_change.regulatory_update)

	def find_affected_controls(self):
		"""
		Find controls potentially affected by this change.

		Returns:
			list: List of match dicts with:
				- control: Control Activity name
				- confidence: Match confidence (0-100)
				- method: How the match was found
				- matched_on: What triggered the match
		"""
		affected = []

		# Method 1: Citation matching (highest confidence)
		citation_matches = self._match_by_citations()
		affected.extend(citation_matches)

		# Method 2: Keyword matching
		keyword_matches = self._match_by_keywords()
		affected.extend(keyword_matches)

		# Method 3: Semantic similarity (if AI enabled)
		if self._is_ai_enabled():
			semantic_matches = self._match_by_semantics()
			affected.extend(semantic_matches)

		# Deduplicate and merge confidence scores
		return self._merge_matches(affected)

	def _match_by_citations(self):
		"""
		Match controls by regulatory citations.

		Looks for controls that reference the same regulatory
		citations mentioned in the change.

		Returns:
			list: List of match dicts
		"""
		matches = []

		# Extract citations from change
		from ..parsers.document_parser import DocumentParser

		change_text = f"{self.change.summary_of_change or ''} {self.change.new_text or ''}"
		parser = DocumentParser(change_text)
		citations = parser.extract_citations()

		if not citations:
			# Try from stored citations
			if self.change.affected_citations:
				citations = [c.strip() for c in self.change.affected_citations.split(",")]

		if not citations:
			return matches

		# Get all controls with their descriptions
		controls = frappe.get_all(
			"Control Activity",
			fields=["name", "control_name", "description", "evidence_requirements", "control_procedure"],
			filters={"status": ["!=", "Deprecated"]},
		)

		for control in controls:
			# Build searchable text
			control_text = " ".join(
				filter(
					None,
					[
						control.control_name or "",
						control.description or "",
						control.evidence_requirements or "",
						control.control_procedure or "",
					],
				)
			).upper()

			# Check each citation
			for citation in citations:
				citation_upper = citation.upper()
				if citation_upper in control_text:
					matches.append(
						{
							"control": control.name,
							"confidence": 90.0,
							"method": "citation",
							"matched_on": citation,
						}
					)
					break  # One match per control

		return matches

	def _match_by_keywords(self):
		"""
		Match controls by keyword overlap.

		Uses TF-IDF style matching to find controls with
		similar terminology to the regulatory change.

		Returns:
			list: List of match dicts
		"""
		matches = []

		# Get change keywords
		change_text = f"{self.change.summary_of_change or ''} {self.change.new_text or ''}"

		if not change_text.strip():
			return matches

		# Extract keywords from change
		from ..parsers.document_parser import DocumentParser

		parser = DocumentParser(change_text)
		change_keywords = set(parser.extract_keywords(top_n=20))

		if not change_keywords:
			# Fallback: simple word extraction
			change_keywords = set(change_text.lower().split())

		# Filter out common words
		stop_words = {
			"the",
			"a",
			"an",
			"and",
			"or",
			"but",
			"in",
			"on",
			"at",
			"to",
			"for",
			"of",
			"with",
			"by",
			"from",
			"as",
			"is",
			"was",
		}
		change_keywords = change_keywords - stop_words

		if not change_keywords:
			return matches

		# Get all controls
		controls = frappe.get_all(
			"Control Activity",
			fields=["name", "control_name", "description", "evidence_requirements", "control_procedure"],
			filters={"status": ["!=", "Deprecated"]},
		)

		for control in controls:
			# Build control text
			control_text = " ".join(
				filter(
					None,
					[
						control.control_name or "",
						control.description or "",
						control.evidence_requirements or "",
						control.control_procedure or "",
					],
				)
			).lower()

			control_words = set(control_text.split()) - stop_words

			if not control_words:
				continue

			# Calculate Jaccard similarity
			intersection = change_keywords & control_words
			union = change_keywords | control_words

			if union:
				similarity = len(intersection) / len(union)

				# Only include if similarity above threshold
				if similarity > 0.05:  # 5% minimum overlap
					confidence = min(flt(similarity * 100, 2) * 2, 80)

					matched_keywords = list(intersection)[:5]

					matches.append(
						{
							"control": control.name,
							"confidence": confidence,
							"method": "keyword",
							"matched_on": ", ".join(matched_keywords),
						}
					)

		return matches

	def _match_by_semantics(self):
		"""
		Match controls using semantic similarity.

		Uses AI embeddings to find conceptually similar controls
		even without keyword overlap.

		Returns:
			list: List of match dicts
		"""
		matches = []

		try:
			from sentence_transformers import SentenceTransformer
			from sklearn.metrics.pairwise import cosine_similarity

			model = SentenceTransformer("all-MiniLM-L6-v2")

			# Get change embedding
			change_text = f"{self.change.summary_of_change or ''} {self.change.new_text or ''}"

			if not change_text.strip():
				return matches

			change_embedding = model.encode([change_text])[0]

			# Get all controls
			controls = frappe.get_all(
				"Control Activity",
				fields=["name", "control_name", "description", "evidence_requirements"],
				filters={"status": ["!=", "Deprecated"]},
			)

			for control in controls:
				control_text = " ".join(
					filter(
						None,
						[
							control.control_name or "",
							control.description or "",
							control.evidence_requirements or "",
						],
					)
				)

				if not control_text.strip():
					continue

				control_embedding = model.encode([control_text])[0]

				similarity = cosine_similarity([change_embedding], [control_embedding])[0][0]

				# Only include if similarity above threshold
				if similarity > 0.3:  # 30% minimum semantic similarity
					confidence = flt(similarity * 100, 2)

					matches.append(
						{
							"control": control.name,
							"confidence": confidence,
							"method": "semantic",
							"matched_on": f"Semantic similarity: {confidence:.1f}%",
						}
					)

		except ImportError:
			pass
		except Exception as e:
			frappe.log_error(message=str(e), title=_("Semantic Matching Error"))

		return matches

	def _is_ai_enabled(self):
		"""
		Check if AI features are enabled in settings.

		Returns:
			bool: True if AI features should be used
		"""
		try:
			settings = frappe.get_single("AI Provider Settings")
			return settings.enabled and settings.enable_semantic_search
		except Exception:
			return False

	def _merge_matches(self, matches):
		"""
		Merge and deduplicate matches.

		When same control matched by multiple methods,
		keep the highest confidence.

		Args:
			matches: List of match dicts

		Returns:
			list: Deduplicated matches sorted by confidence
		"""
		merged = {}

		for match in matches:
			control = match["control"]
			if control in merged:
				# Keep higher confidence
				if match["confidence"] > merged[control]["confidence"]:
					merged[control] = match
				# If same confidence, prefer citation > keyword > semantic
				elif match["confidence"] == merged[control]["confidence"]:
					method_priority = {"citation": 3, "keyword": 2, "semantic": 1}
					if method_priority.get(match["method"], 0) > method_priority.get(
						merged[control]["method"], 0
					):
						merged[control] = match
			else:
				merged[control] = match

		# Sort by confidence descending
		sorted_matches = sorted(merged.values(), key=lambda x: x["confidence"], reverse=True)

		return sorted_matches

	def create_impact_assessments(self, min_confidence=50.0):
		"""
		Create impact assessment documents for affected controls.

		Args:
			min_confidence: Minimum confidence to create assessment

		Returns:
			list: Names of created assessment documents
		"""
		affected_controls = self.find_affected_controls()
		created = []

		for match in affected_controls:
			if match["confidence"] < min_confidence:
				continue

			# Check if assessment already exists
			exists = frappe.db.exists(
				"Regulatory Impact Assessment",
				{"regulatory_change": self.change.name, "control_activity": match["control"]},
			)

			if exists:
				continue

			# Determine impact type based on change severity
			impact_type = self._determine_impact_type(match)

			# Build matched info
			matched_citations = ""
			matched_keywords = ""

			if match["method"] == "citation":
				matched_citations = match["matched_on"]
			elif match["method"] == "keyword":
				matched_keywords = match["matched_on"]

			try:
				doc = frappe.get_doc(
					{
						"doctype": "Regulatory Impact Assessment",
						"regulatory_change": self.change.name,
						"regulatory_update": self.change.regulatory_update,
						"control_activity": match["control"],
						"mapping_method": self._map_method_name(match["method"]),
						"confidence_score": match["confidence"],
						"matched_citations": matched_citations,
						"matched_keywords": matched_keywords,
						"impact_type": impact_type,
						"gap_identified": impact_type == "New Control Needed",
						"status": "Pending",
					}
				)
				doc.insert(ignore_permissions=True)
				created.append(doc.name)

			except Exception as e:
				frappe.log_error(
					message=f"Error creating impact assessment: {str(e)}",
					title=_("Impact Assessment Creation Error"),
				)

		frappe.db.commit()
		return created

	def _determine_impact_type(self, match):
		"""
		Determine type of impact on control.

		Args:
			match: Match dict with control and confidence

		Returns:
			str: Impact type
		"""
		severity = self.change.severity

		# High confidence + critical severity = likely needs new control
		if match["confidence"] >= 80 and severity == "Critical":
			return "New Control Needed"

		if severity in ("Critical", "Major"):
			return "Modify Existing"

		if severity == "Moderate":
			return "Review Required"

		return "Review Required"

	def _map_method_name(self, method):
		"""
		Map internal method name to user-friendly name.

		Args:
			method: Internal method name

		Returns:
			str: User-friendly method name
		"""
		mapping = {"citation": "Automatic", "keyword": "Automatic", "semantic": "AI Suggested"}
		return mapping.get(method, "Automatic")
