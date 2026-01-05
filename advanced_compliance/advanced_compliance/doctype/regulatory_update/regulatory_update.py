# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, getdate, nowdate


class RegulatoryUpdate(Document):
	"""
	DocType for storing ingested regulatory updates.

	Stores regulatory content fetched from external sources,
	along with extracted metadata like citations, keywords, and entities.
	"""

	def validate(self):
		"""Validate regulatory update."""
		self.calculate_days_until_effective()

	def before_save(self):
		"""Actions before saving."""
		if self.status == "Reviewed" and not self.processed_date:
			self.processed_date = frappe.utils.now_datetime()

	def calculate_days_until_effective(self):
		"""Calculate days until effective date."""
		if self.effective_date:
			self.days_until_effective = date_diff(getdate(self.effective_date), getdate(nowdate()))
		else:
			self.days_until_effective = None

	def extract_metadata(self):
		"""
		Extract metadata from full text using document parser.

		Extracts citations, keywords, entities, and effective dates.
		"""
		if not self.full_text:
			return

		from advanced_compliance.advanced_compliance.regulatory_feeds.parsers.document_parser import (
			DocumentParser,
		)

		parser = DocumentParser(self.full_text)

		# Extract citations
		citations = parser.extract_citations()
		if citations:
			self.citations = ", ".join(citations)

		# Extract keywords
		keywords = parser.extract_keywords(top_n=10)
		if keywords:
			self.extracted_keywords = ", ".join(keywords)

		# Extract effective date if not already set
		if not self.effective_date:
			effective_date = parser.extract_effective_date()
			if effective_date:
				self.effective_date = effective_date

		# Extract entities
		entities = parser.extract_entities()
		if entities:
			entity_str = []
			for ent_type, ent_list in entities.items():
				if ent_list:
					unique_ents = list(set(ent_list))[:5]
					entity_str.append(f"{ent_type}: {', '.join(unique_ents)}")
			if entity_str:
				self.extracted_entities = "; ".join(entity_str)

		self.save(ignore_permissions=True)

	def analyze_impact(self):
		"""
		Analyze impact of this update on existing controls.

		Creates Regulatory Impact Assessment documents for affected controls.

		Returns:
			list: Names of created impact assessments
		"""
		from advanced_compliance.advanced_compliance.regulatory_feeds.mapping.impact_mapper import (
			ImpactMapper,
		)

		# Get all changes for this update
		changes = frappe.get_all("Regulatory Change", filters={"regulatory_update": self.name}, pluck="name")

		all_assessments = []

		for change_name in changes:
			# Skip if change was deleted (race condition safety)
			if not frappe.db.exists("Regulatory Change", change_name):
				frappe.log_error(
					message=f"Regulatory Change {change_name} does not exist for update {self.name}",
					title="Impact Analysis Skipped",
				)
				continue

			change_doc = frappe.get_doc("Regulatory Change", change_name)
			mapper = ImpactMapper(change_doc)
			assessments = mapper.create_impact_assessments()
			all_assessments.extend(assessments)

		if all_assessments:
			self.status = "Action Required"
			self.save(ignore_permissions=True)

		return all_assessments

	def get_affected_controls(self):
		"""
		Get controls affected by this regulatory update.

		Returns:
			list: Control Activity documents
		"""
		assessments = frappe.get_all(
			"Regulatory Impact Assessment",
			filters={"regulatory_update": self.name},
			fields=["control_activity"],
		)

		control_names = list(set([a.control_activity for a in assessments]))

		return frappe.get_all(
			"Control Activity",
			filters={"name": ["in", control_names]},
			fields=["name", "control_name", "control_owner", "status"],
		)
