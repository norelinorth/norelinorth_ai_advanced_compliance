# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Change Detector

Algorithms for detecting and analyzing changes between regulatory text versions.
Includes both text-based and semantic comparison methods.
"""

import difflib

import frappe
from frappe import _
from frappe.utils import flt


class ChangeDetector:
	"""
	Detect and analyze changes between regulatory versions.

	Uses difflib for text comparison and provides change classification.
	"""

	def __init__(self, old_text, new_text):
		"""
		Initialize with old and new text versions.

		Args:
			old_text: Previous version text
			new_text: New version text
		"""
		self.old_text = old_text or ""
		self.new_text = new_text or ""
		self.old_lines = self.old_text.splitlines()
		self.new_lines = self.new_text.splitlines()

	def detect_changes(self):
		"""
		Detect all changes between versions.

		Returns:
			list: List of change dicts with structure:
				- change_type: Type of change
				- removed_text: Lines removed
				- added_text: Lines added
				- severity: Change severity
				- summary: Human-readable summary
		"""
		changes = []

		differ = difflib.unified_diff(self.old_lines, self.new_lines, lineterm="")

		current_change = None
		diff_lines = list(differ)

		for line in diff_lines:
			if line.startswith("---") or line.startswith("+++"):
				continue
			elif line.startswith("@@"):
				if current_change:
					changes.append(current_change)
				current_change = {
					"change_type": "Amendment",
					"removed_text": [],
					"added_text": [],
					"location": line,
				}
			elif line.startswith("-") and current_change is not None:
				current_change["removed_text"].append(line[1:])
			elif line.startswith("+") and current_change is not None:
				current_change["added_text"].append(line[1:])

		if current_change:
			changes.append(current_change)

		# Classify each change
		for change in changes:
			change["severity"] = self._classify_severity(change)
			change["summary"] = self._summarize_change(change)
			change["change_type"] = self._classify_change_type(change)

		return changes

	def calculate_similarity(self):
		"""
		Calculate overall similarity ratio.

		Returns:
			float: Similarity ratio 0.0 to 1.0
		"""
		if not self.old_text and not self.new_text:
			return 1.0

		if not self.old_text or not self.new_text:
			return 0.0

		matcher = difflib.SequenceMatcher(None, self.old_text, self.new_text)
		return matcher.ratio()

	def get_diff_html(self):
		"""
		Generate HTML diff for display.

		Returns:
			str: HTML formatted diff
		"""
		differ = difflib.HtmlDiff()
		return differ.make_table(
			self.old_lines, self.new_lines, fromdesc="Previous Version", todesc="New Version"
		)

	def _classify_severity(self, change):
		"""
		Classify change severity.

		Args:
			change: Change dict with removed_text and added_text

		Returns:
			str: Severity level (Critical, Major, Moderate, Minor)
		"""
		removed = "\n".join(change.get("removed_text", []))
		added = "\n".join(change.get("added_text", []))

		removed_lower = removed.lower()
		added_lower = added.lower()

		# Critical indicators - new mandatory requirements
		critical_keywords = [
			"prohibited",
			"violation",
			"penalty",
			"fine",
			"material weakness",
			"significant deficiency",
		]

		for keyword in critical_keywords:
			if keyword in added_lower and keyword not in removed_lower:
				return "Critical"

		# Major indicators - obligation changes
		major_keywords = ["must", "shall", "required", "mandatory"]

		for keyword in major_keywords:
			if keyword in added_lower and keyword not in removed_lower:
				return "Major"

		# Weakening from mandatory to optional
		optional_keywords = ["may", "should", "can"]
		for mandatory in major_keywords:
			for optional in optional_keywords:
				if mandatory in removed_lower and optional in added_lower:
					return "Major"

		# Calculate change magnitude
		total_change = len(removed) + len(added)

		if total_change > 2000:
			return "Major"
		elif total_change > 500:
			return "Moderate"
		else:
			return "Minor"

	def _classify_change_type(self, change):
		"""
		Classify the type of change.

		Args:
			change: Change dict

		Returns:
			str: Change type
		"""
		removed = change.get("removed_text", [])
		added = change.get("added_text", [])

		if not removed and added:
			return "New Requirement"
		elif removed and not added:
			return "Removal"
		elif len(added) > len(removed) * 2:
			return "New Requirement"
		elif len(removed) > len(added) * 2:
			return "Removal"
		else:
			# Check if mostly word changes
			removed_text = "\n".join(removed)
			added_text = "\n".join(added)

			# Calculate word-level similarity
			removed_words = set(removed_text.lower().split())
			added_words = set(added_text.lower().split())

			common_words = removed_words & added_words
			all_words = removed_words | added_words

			if len(all_words) > 0 and len(common_words) / len(all_words) > 0.8:
				return "Clarification"

			return "Amendment"

	def _summarize_change(self, change):
		"""
		Generate human-readable change summary.

		Args:
			change: Change dict

		Returns:
			str: Summary of change
		"""
		removed_count = len(change.get("removed_text", []))
		added_count = len(change.get("added_text", []))

		if removed_count == 0 and added_count > 0:
			return _("Added {0} new lines").format(added_count)
		elif removed_count > 0 and added_count == 0:
			return _("Removed {0} lines").format(removed_count)
		else:
			return _("Modified: {0} lines removed, {1} lines added").format(removed_count, added_count)

	def detect_obligation_changes(self):
		"""
		Specifically detect changes in obligation level.

		Returns:
			list: List of obligation changes found
		"""
		changes = []

		# Words indicating stronger obligations
		strong_obligations = ["must", "shall", "required", "mandatory", "will"]
		weak_obligations = ["may", "should", "can", "might", "could"]

		old_lower = self.old_text.lower()
		new_lower = self.new_text.lower()

		# Check for strengthening
		for weak in weak_obligations:
			for strong in strong_obligations:
				# Count occurrences
				old_weak_count = old_lower.count(weak)
				new_weak_count = new_lower.count(weak)
				old_strong_count = old_lower.count(strong)
				new_strong_count = new_lower.count(strong)

				# Strengthening: weak decreased, strong increased
				if old_weak_count > new_weak_count and new_strong_count > old_strong_count:
					changes.append(
						{
							"type": "strengthened",
							"from": weak,
							"to": strong,
							"description": _("Obligation strengthened: '{0}' changed to '{1}'").format(
								weak, strong
							),
						}
					)

				# Weakening: strong decreased, weak increased
				if old_strong_count > new_strong_count and new_weak_count > old_weak_count:
					changes.append(
						{
							"type": "weakened",
							"from": strong,
							"to": weak,
							"description": _("Obligation weakened: '{0}' changed to '{1}'").format(
								strong, weak
							),
						}
					)

		return changes


class SemanticChangeDetector:
	"""
	Detect semantic (meaning) changes using AI embeddings.

	Uses sentence transformers to compare meaning rather than
	just text similarity.
	"""

	def __init__(self):
		"""Initialize with embedding model."""
		self.model = None
		self._load_model()

	def _load_model(self):
		"""Load sentence transformer model."""
		try:
			from sentence_transformers import SentenceTransformer

			self.model = SentenceTransformer("all-MiniLM-L6-v2")
		except ImportError:
			pass
		except Exception as e:
			frappe.log_error(message=str(e), title=_("Semantic Model Load Error"))

	def is_available(self):
		"""Check if semantic analysis is available."""
		return self.model is not None

	def semantic_similarity(self, text1, text2):
		"""
		Calculate semantic similarity between texts.

		Args:
			text1: First text
			text2: Second text

		Returns:
			float: Similarity score 0.0 to 1.0
		"""
		if not self.model:
			return 0.0

		if not text1 or not text2:
			return 0.0

		try:
			from sklearn.metrics.pairwise import cosine_similarity

			embeddings = self.model.encode([text1, text2])
			similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]

			return flt(similarity, 4)

		except Exception as e:
			frappe.log_error(message=str(e), title=_("Semantic Similarity Error"))
			return 0.0

	def detect_meaning_changes(self, old_text, new_text, threshold=0.85):
		"""
		Detect if meaning changed significantly.

		Args:
			old_text: Previous text
			new_text: New text
			threshold: Similarity threshold (below = meaning changed)

		Returns:
			dict: Analysis results with:
				- semantic_similarity: 0.0-1.0 score
				- meaning_changed: bool
				- change_magnitude: significant/moderate/minor
		"""
		similarity = self.semantic_similarity(old_text, new_text)

		if similarity < 0.5:
			magnitude = "significant"
		elif similarity < 0.7:
			magnitude = "moderate"
		elif similarity < threshold:
			magnitude = "minor"
		else:
			magnitude = "negligible"

		return {
			"semantic_similarity": similarity,
			"meaning_changed": similarity < threshold,
			"change_magnitude": magnitude,
		}

	def compare_sections(self, old_sections, new_sections):
		"""
		Compare corresponding sections for semantic changes.

		Args:
			old_sections: Dict of section name -> text
			new_sections: Dict of section name -> text

		Returns:
			list: Section comparison results
		"""
		results = []

		all_sections = set(old_sections.keys()) | set(new_sections.keys())

		for section in all_sections:
			old_text = old_sections.get(section, "")
			new_text = new_sections.get(section, "")

			if not old_text and new_text:
				results.append({"section": section, "status": "added", "similarity": 0.0})
			elif old_text and not new_text:
				results.append({"section": section, "status": "removed", "similarity": 0.0})
			else:
				similarity = self.semantic_similarity(old_text, new_text)
				status = "unchanged" if similarity > 0.85 else "modified"
				results.append({"section": section, "status": status, "similarity": similarity})

		return results
