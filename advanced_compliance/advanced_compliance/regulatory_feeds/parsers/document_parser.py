# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Document Parser

Extracts structured data from regulatory documents including
citations, effective dates, keywords, and named entities.
"""

import re

import frappe
from frappe import _
from frappe.utils import getdate


class DocumentParser:
	"""
	Parse regulatory documents to extract structured data.

	Extracts:
	- Regulatory citations (CFR, ASC, PCAOB, etc.)
	- Effective/compliance dates
	- Keywords using TF-IDF
	- Named entities (organizations, dates, regulations)
	"""

	# Common regulatory citation patterns
	CITATION_PATTERNS = [
		# CFR citations: 17 CFR 240.10b-5, 17 CFR Part 240
		r"\d+\s*CFR\s*(?:Part\s*)?\d+(?:\.\d+[a-z]?(?:-\d+)?)?",
		# Section references: Section 302(a), Section 404
		r"Section\s*\d+(?:\([a-z]\))?(?:\([0-9]+\))?",
		# SEC Rules: Rule 10b-5, Rule 144
		r"Rule\s*\d+[a-z]?(?:-\d+)?",
		# ASC citations: ASC 606-10-25, ASC 842
		r"ASC\s*\d+(?:-\d+)?(?:-\d+)?",
		# PCAOB standards: PCAOB AS 2201, AS 1301
		r"(?:PCAOB\s*)?AS\s*\d+",
		# SOX sections: SOX 302, SOX 404
		r"SOX\s*\d+",
		# GAAP references
		r"GAAP\s*(?:Section\s*)?\d+",
		# ISA standards: ISA 315, ISA 700
		r"ISA\s*\d+",
	]

	# Date patterns for effective dates
	EFFECTIVE_DATE_PATTERNS = [
		# "effective January 1, 2025" or "effective on January 1, 2025"
		r"effective\s+(?:on\s+)?(\w+\s+\d{1,2},?\s+\d{4})",
		# "effective as of January 1, 2025"
		r"effective\s+as\s+of\s+(\w+\s+\d{1,2},?\s+\d{4})",
		# "effective 01/01/2025" or "effective 1/1/2025"
		r"effective\s+(?:on\s+)?(\d{1,2}/\d{1,2}/\d{4})",
		# "compliance date: January 1, 2025"
		r"compliance\s+date[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
		# "becomes effective January 1, 2025"
		r"becomes\s+effective\s+(\w+\s+\d{1,2},?\s+\d{4})",
		# ISO format: "effective 2025-01-01"
		r"effective\s+(?:on\s+)?(\d{4}-\d{2}-\d{2})",
	]

	def __init__(self, text):
		"""
		Initialize parser with document text.

		Args:
			text: Full text of regulatory document
		"""
		self.text = text or ""
		self.text_lower = self.text.lower()

	def extract_citations(self):
		"""
		Extract regulatory citations from text.

		Returns:
			list: List of unique citation strings found
		"""
		citations = []

		for pattern in self.CITATION_PATTERNS:
			matches = re.findall(pattern, self.text, re.IGNORECASE)
			citations.extend(matches)

		# Normalize and deduplicate
		normalized = []
		seen = set()

		for citation in citations:
			# Normalize spacing
			normalized_citation = re.sub(r"\s+", " ", citation.strip())
			normalized_citation = normalized_citation.upper()

			if normalized_citation not in seen:
				seen.add(normalized_citation)
				normalized.append(normalized_citation)

		return normalized

	def extract_effective_date(self):
		"""
		Extract effective/compliance date from text.

		Returns:
			date or None: Extracted effective date
		"""
		for pattern in self.EFFECTIVE_DATE_PATTERNS:
			match = re.search(pattern, self.text_lower)
			if match:
				date_str = match.group(1)
				parsed_date = self._parse_date_string(date_str)
				if parsed_date:
					return parsed_date

		return None

	def _parse_date_string(self, date_str):
		"""
		Parse date string to date object.

		Args:
			date_str: Date string in various formats

		Returns:
			date or None: Parsed date
		"""
		# Try dateparser first (handles natural language dates)
		try:
			import dateparser

			parsed = dateparser.parse(date_str)
			if parsed:
				return getdate(parsed)
		except ImportError:
			# dateparser library not installed - fallback to manual parsing
			pass
		except Exception as e:
			frappe.log_error(
				message=f"Failed to parse date '{date_str}' using dateparser: {str(e)}",
				title="Document Parser Date Error",
			)

		# Fallback: try common formats
		from datetime import datetime

		formats = [
			"%B %d, %Y",  # January 1, 2025
			"%B %d %Y",  # January 1 2025
			"%m/%d/%Y",  # 01/01/2025
			"%Y-%m-%d",  # 2025-01-01
			"%d %B %Y",  # 1 January 2025
		]

		for fmt in formats:
			try:
				parsed = datetime.strptime(date_str.strip(), fmt)
				return getdate(parsed)
			except ValueError:
				continue

		return None

	def extract_keywords(self, top_n=10):
		"""
		Extract key terms using TF-IDF approach.

		Args:
			top_n: Number of top keywords to return

		Returns:
			list: Top keywords
		"""
		if not self.text or len(self.text) < 50:
			return []

		try:
			from sklearn.feature_extraction.text import TfidfVectorizer

			# Configure vectorizer
			vectorizer = TfidfVectorizer(
				max_features=top_n, stop_words="english", ngram_range=(1, 2), min_df=1, max_df=0.95
			)

			# Fit and get feature names
			vectorizer.fit_transform([self.text])
			keywords = vectorizer.get_feature_names_out().tolist()

			return keywords

		except ImportError:
			# Fallback: simple word frequency (sklearn not installed)
			return self._simple_keyword_extraction(top_n)
		except Exception as e:
			frappe.log_error(
				message=f"Failed to extract keywords using TF-IDF: {str(e)}",
				title="Document Parser Keyword Error",
			)
			return self._simple_keyword_extraction(top_n)

	def _simple_keyword_extraction(self, top_n=10):
		"""
		Simple keyword extraction without sklearn.

		Args:
			top_n: Number of keywords to return

		Returns:
			list: Keywords
		"""
		# Common English stop words
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
			"are",
			"were",
			"been",
			"be",
			"have",
			"has",
			"had",
			"do",
			"does",
			"did",
			"will",
			"would",
			"could",
			"should",
			"may",
			"might",
			"this",
			"that",
			"these",
			"those",
			"it",
			"its",
			"they",
			"their",
			"we",
			"our",
			"you",
			"your",
			"he",
			"she",
			"him",
			"her",
			"his",
			"which",
			"who",
			"whom",
			"what",
			"when",
			"where",
			"why",
			"how",
			"all",
			"each",
			"every",
			"both",
			"few",
			"more",
			"most",
			"other",
			"some",
			"such",
			"no",
			"nor",
			"not",
			"only",
			"same",
			"so",
			"than",
			"too",
			"very",
			"can",
			"just",
			"also",
			"any",
			"if",
			"then",
			"into",
			"about",
			"over",
			"under",
			"after",
		}

		# Tokenize and count
		words = re.findall(r"\b[a-zA-Z]{3,}\b", self.text_lower)
		word_counts = {}

		for word in words:
			if word not in stop_words:
				word_counts[word] = word_counts.get(word, 0) + 1

		# Sort by frequency
		sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)

		return [word for word, count in sorted_words[:top_n]]

	def extract_entities(self):
		"""
		Extract named entities (organizations, dates, regulations).

		Returns:
			dict: Entities by type
		"""
		entities = {"organizations": [], "dates": [], "regulations": []}

		# Try spaCy for NER
		try:
			import spacy

			try:
				nlp = spacy.load("en_core_web_sm")
			except OSError:
				# Model not installed, return empty
				return entities

			# Limit text for performance
			text_to_process = self.text[:100000]
			doc = nlp(text_to_process)

			for ent in doc.ents:
				if ent.label_ == "ORG":
					entities["organizations"].append(ent.text)
				elif ent.label_ == "DATE":
					entities["dates"].append(ent.text)
				elif ent.label_ == "LAW":
					entities["regulations"].append(ent.text)

			# Deduplicate
			for key in entities:
				entities[key] = list(set(entities[key]))[:10]

		except ImportError:
			# spaCy not available, use regex fallback
			entities["regulations"] = self.extract_citations()[:10]

		return entities

	def generate_summary(self, max_sentences=3):
		"""
		Generate extractive summary of document.

		Args:
			max_sentences: Maximum sentences in summary

		Returns:
			str: Summary text
		"""
		if not self.text:
			return ""

		# Split into sentences
		sentences = re.split(r"(?<=[.!?])\s+", self.text)

		# Filter short sentences
		sentences = [s for s in sentences if len(s) > 30]

		# Take first N sentences
		summary_sentences = sentences[:max_sentences]

		return " ".join(summary_sentences)

	def detect_obligation_level(self):
		"""
		Detect obligation level in the text.

		Returns:
			dict: Obligation analysis with counts
		"""
		mandatory_words = [
			"must",
			"shall",
			"required",
			"mandatory",
			"will",
			"need to",
			"have to",
			"obligated",
		]

		permissive_words = [
			"may",
			"should",
			"can",
			"might",
			"could",
			"recommended",
			"encouraged",
			"suggested",
		]

		prohibitive_words = ["prohibited", "forbidden", "must not", "shall not", "may not", "cannot"]

		text_lower = self.text_lower

		return {
			"mandatory": sum(text_lower.count(w) for w in mandatory_words),
			"permissive": sum(text_lower.count(w) for w in permissive_words),
			"prohibitive": sum(text_lower.count(w) for w in prohibitive_words),
		}


class PDFParser:
	"""
	Parse PDF regulatory documents.

	Extracts text content from PDF files for analysis.
	"""

	def __init__(self, file_path):
		"""
		Initialize with PDF file path.

		Args:
			file_path: Path to PDF file
		"""
		self.file_path = file_path

	def extract_text(self):
		"""
		Extract text from PDF.

		Returns:
			str: Extracted text content
		"""
		try:
			import pdfplumber

			text_parts = []
			with pdfplumber.open(self.file_path) as pdf:
				for page in pdf.pages:
					text = page.extract_text()
					if text:
						text_parts.append(text)

			return "\n".join(text_parts)

		except ImportError:
			frappe.log_error(
				message="pdfplumber not installed. " "Install with: pip install pdfplumber",
				title=_("PDF Parser Error"),
			)
			return ""

		except Exception as e:
			frappe.log_error(message=str(e), title=_("PDF Parse Error"))
			return ""

	def extract_tables(self):
		"""
		Extract tables from PDF.

		Returns:
			list: List of tables (each as list of rows)
		"""
		try:
			import pdfplumber

			tables = []
			with pdfplumber.open(self.file_path) as pdf:
				for page in pdf.pages:
					page_tables = page.extract_tables()
					if page_tables:
						tables.extend(page_tables)

			return tables

		except ImportError:
			# pdfplumber not installed
			return []
		except Exception as e:
			frappe.log_error(
				message=f"Failed to extract tables from PDF: {str(e)}",
				title="Document Parser Table Extraction Error",
			)
			return []
