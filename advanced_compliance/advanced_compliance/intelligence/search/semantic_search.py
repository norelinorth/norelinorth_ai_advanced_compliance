"""
Semantic Search.

Vector embedding-based similarity search for compliance documents.
"""

import json
import math

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate


class SemanticSearch:
	"""
	Semantic search using vector embeddings.

	Supports searching across:
	- Control Activity descriptions
	- Compliance Risk descriptions
	- Deficiency details
	- Test Execution notes
	- Compliance Framework requirements
	"""

	# Supported DocTypes and their text fields
	SEARCHABLE_DOCTYPES = {
		"Control Activity": ["control_name", "description", "objective"],
		"Risk Register Entry": ["risk_name", "description", "risk_category"],
		"Deficiency": ["title", "description", "root_cause"],
		"Test Execution": ["test_description", "findings", "conclusion"],
		"Compliance Framework": ["framework_name", "description"],
		"Framework Requirement": ["requirement_text", "description", "guidance"],
	}

	def __init__(self):
		"""Initialize semantic search."""
		self.settings = self._get_settings()
		self.embedding_model = None
		self.embedding_dimension = 384  # Default for sentence-transformers

		if self.settings and cint(self.settings.embedding_dimension):
			self.embedding_dimension = cint(self.settings.embedding_dimension)

	def _get_settings(self):
		"""Get AI provider settings."""
		try:
			from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
				get_ai_settings,
			)

			return get_ai_settings()
		except Exception as e:
			frappe.log_error(
				message=f"Failed to get AI settings: {str(e)}\n{frappe.get_traceback()}",
				title="Semantic Search Initialization Error",
			)
			return None

	def search(self, query, doctypes=None, limit=10, threshold=0.5):
		"""
		Search for documents similar to query.

		Args:
		    query: Search query string
		    doctypes: List of DocTypes to search (None = all)
		    limit: Maximum results to return
		    threshold: Minimum similarity score (0-1)

		Returns:
		    List of search results with similarity scores
		"""
		if not query:
			return []

		# Generate query embedding
		query_embedding = self.generate_embedding(query)
		if not query_embedding:
			# Fall back to text search
			return self._text_search_fallback(query, doctypes, limit)

		# Get candidate embeddings
		filters = {}
		if doctypes:
			filters["source_doctype"] = ["in", doctypes]

		embeddings = frappe.get_all(
			"Document Embedding",
			filters=filters,
			fields=[
				"name",
				"source_doctype",
				"source_document",
				"source_field",
				"embedding_vector",
				"source_text",
			],
		)

		# Calculate similarities
		results = []
		for emb in embeddings:
			if not emb.embedding_vector:
				continue

			try:
				doc_embedding = json.loads(emb.embedding_vector)
				similarity = self._cosine_similarity(query_embedding, doc_embedding)

				if similarity >= threshold:
					results.append(
						{
							"doctype": emb.source_doctype,
							"document": emb.source_document,
							"field": emb.source_field,
							"preview": emb.source_text,
							"similarity": round(similarity, 4),
						}
					)
			except (json.JSONDecodeError, TypeError):
				continue

		# Sort by similarity
		results.sort(key=lambda x: x["similarity"], reverse=True)

		return results[:limit]

	def generate_embedding(self, text):
		"""
		Generate embedding vector for text.

		Tries API-based embeddings first (if configured), then falls back to local.

		Args:
		    text: Text to embed

		Returns:
		    List of floats (embedding vector) or None
		"""
		if not text:
			return None

		# Try using configured embedding provider (via AI Assistant app)
		if self._is_ai_available():
			embedding = self._generate_api_embedding(text)
			if embedding:
				return embedding

		# Fall back to local sentence-transformers
		embedding = self._generate_local_embedding(text)
		if embedding:
			return embedding

		return None

	def _is_ai_available(self):
		"""Check if AI Assistant app is available and configured."""
		try:
			from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
				is_ai_assistant_available,
			)

			return is_ai_assistant_available()
		except Exception as e:
			frappe.log_error(
				message=f"Failed to check AI availability: {str(e)}\n{frappe.get_traceback()}",
				title="Semantic Search AI Check Error",
			)
			return False

	def _get_ai_provider(self):
		"""Get AI provider name from AI Assistant app."""
		try:
			from norelinorth_ai_assistant.ai_provider_resolver import AIProviderResolver

			config = AIProviderResolver.get_ai_provider_config()
			return config.get("provider_name", "")
		except Exception as e:
			frappe.log_error(
				message=f"Failed to get AI provider: {str(e)}\n{frappe.get_traceback()}",
				title="Semantic Search Provider Error",
			)
			return None

	def _generate_api_embedding(self, text):
		"""Generate embedding using API provider (OpenAI, etc.)."""
		try:
			provider = self._get_ai_provider()

			if provider and "openai" in provider.lower():
				return self._openai_embedding(text)
			else:
				# Other providers may not support embeddings, use local
				return None
		except Exception as e:
			frappe.log_error(
				message=f"API embedding error: {str(e)}", title="Semantic Search Embedding Error"
			)
			return None

	def _openai_embedding(self, text):
		"""Generate embedding using OpenAI API (with security fix)."""
		try:
			import openai

			# SECURITY FIX: Use public get_api_credentials() method for secure access
			from norelinorth_ai_assistant.ai_provider_resolver import AIProviderResolver

			# Use public method to get credentials
			api_key, provider, model = AIProviderResolver.get_api_credentials()

			if not api_key:
				return None

			client = openai.OpenAI(api_key=api_key)
			embedding_model = getattr(self.settings, "embedding_model", None) or "text-embedding-3-small"

			response = client.embeddings.create(input=text, model=embedding_model)

			# Safe access - check response has data before accessing
			if response.data and len(response.data) > 0:
				return response.data[0].embedding
			return None
		except ImportError:
			# openai not installed
			return None
		except Exception as e:
			frappe.log_error(message=f"OpenAI embedding error: {str(e)}", title=_("OpenAI Embedding Error"))
			return None

	def _generate_local_embedding(self, text):
		"""Generate embedding using local sentence-transformers."""
		try:
			from sentence_transformers import SentenceTransformer

			if not self.embedding_model:
				model_name = "all-MiniLM-L6-v2"
				# Check if settings has embedding_model field
				if (
					self.settings
					and hasattr(self.settings, "embedding_model")
					and self.settings.embedding_model
				):
					model_name = self.settings.embedding_model
				self.embedding_model = SentenceTransformer(model_name)

			embedding = self.embedding_model.encode(text)
			return embedding.tolist()
		except ImportError:
			# sentence-transformers not installed
			return None
		except Exception as e:
			frappe.log_error(message=f"Local embedding error: {str(e)}", title=_("Local Embedding Error"))
			return None

	def _cosine_similarity(self, vec1, vec2):
		"""Calculate cosine similarity between two vectors."""
		if len(vec1) != len(vec2):
			return 0.0

		dot_product = sum(a * b for a, b in zip(vec1, vec2))
		magnitude1 = math.sqrt(sum(a * a for a in vec1))
		magnitude2 = math.sqrt(sum(b * b for b in vec2))

		if magnitude1 == 0 or magnitude2 == 0:
			return 0.0

		return dot_product / (magnitude1 * magnitude2)

	def _text_search_fallback(self, query, doctypes, limit):
		"""Fallback to simple text search when embeddings unavailable."""
		results = []
		search_doctypes = doctypes or list(self.SEARCHABLE_DOCTYPES.keys())

		for doctype in search_doctypes:
			if doctype not in self.SEARCHABLE_DOCTYPES:
				continue

			if not frappe.has_permission(doctype, "read"):
				continue

			fields = self.SEARCHABLE_DOCTYPES[doctype]

			# Validate all fields exist in the doctype (prevent SQL injection)
			try:
				meta = frappe.get_meta(doctype)
			except frappe.DoesNotExistError:
				# Skip doctypes that don't exist in this installation
				continue

			validated_fields = []
			for field in fields:
				if meta.has_field(field):
					validated_fields.append(field)

			if not validated_fields:
				continue

			try:
				# Build OR filters using Frappe's filter syntax (safe from SQL injection)
				# Format: [["field1", "like", "%query%"], "or", ["field2", "like", "%query%"], ...]
				filters = []
				for i, field in enumerate(validated_fields):
					if i > 0:
						filters.append("or")
					filters.append([field, "like", f"%{query}%"])

				# Use frappe.db.get_list with parameterized filters (standard Frappe pattern)
				docs = frappe.db.get_list(
					doctype,
					filters=filters,
					fields=["name"] + validated_fields,
					limit_page_length=limit,
					as_list=False,
				)

				for doc in docs:
					# Get preview from first non-empty field
					preview = ""
					for field in validated_fields:
						if doc.get(field):
							preview = str(doc[field])[:200]
							break

					results.append(
						{
							"doctype": doctype,
							"document": doc.name,
							"field": validated_fields[0],
							"preview": preview,
							"similarity": 0.5,  # Fixed score for text match
						}
					)
			except Exception as e:
				frappe.log_error(
					message=f"Failed to search {doctype}: {str(e)}\n{frappe.get_traceback()}",
					title="Semantic Search DocType Error",
				)
				continue

		return results[:limit]

	def index_document(self, doctype, docname):
		"""
		Index a document for semantic search.

		Args:
		    doctype: DocType name
		    docname: Document name

		Returns:
		    List of created embedding names
		"""
		if doctype not in self.SEARCHABLE_DOCTYPES:
			return []

		fields = self.SEARCHABLE_DOCTYPES[doctype]
		doc = frappe.get_doc(doctype, docname)
		created = []

		for field in fields:
			text = doc.get(field)
			if not text:
				continue

			# Generate embedding
			embedding = self.generate_embedding(str(text))
			if not embedding:
				continue

			# Check if embedding exists
			existing = frappe.db.get_value(
				"Document Embedding",
				{"source_doctype": doctype, "source_document": docname, "source_field": field},
				"name",
			)

			# Get embedding model name
			embedding_model_name = "local"
			if self.settings and hasattr(self.settings, "embedding_model") and self.settings.embedding_model:
				embedding_model_name = self.settings.embedding_model

			if existing:
				# Update existing
				emb_doc = frappe.get_doc("Document Embedding", existing)
				emb_doc.embedding_vector = json.dumps(embedding)
				emb_doc.source_text = str(text)[:500]
				emb_doc.embedding_model = embedding_model_name
				emb_doc.save(ignore_permissions=True)
				created.append(existing)
			else:
				# Create new
				emb_doc = frappe.get_doc(
					{
						"doctype": "Document Embedding",
						"source_doctype": doctype,
						"source_document": docname,
						"source_field": field,
						"embedding_vector": json.dumps(embedding),
						"source_text": str(text)[:500],
						"embedding_model": embedding_model_name,
						"embedding_dimension": len(embedding),
					}
				)
				emb_doc.flags.ignore_permissions = True
				emb_doc.insert()
				created.append(emb_doc.name)

		return created

	def index_all_documents(self, doctype=None):
		"""
		Index all documents for semantic search.

		Args:
		    doctype: Specific DocType to index (None = all)

		Returns:
		    Summary of indexing
		"""
		doctypes_to_index = [doctype] if doctype else list(self.SEARCHABLE_DOCTYPES.keys())
		summary = {"total_indexed": 0, "by_doctype": {}}

		for dt in doctypes_to_index:
			if dt not in self.SEARCHABLE_DOCTYPES:
				continue

			docs = frappe.get_all(dt, pluck="name")
			count = 0

			for docname in docs:
				try:
					created = self.index_document(dt, docname)
					count += len(created)
				except Exception as e:
					frappe.log_error(
						message=f"Failed to index {dt}/{docname}: {str(e)}",
						title="Semantic Search Indexing Error",
					)

			summary["by_doctype"][dt] = count
			summary["total_indexed"] += count

		frappe.db.commit()
		return summary

	def find_similar_controls(self, control_id, limit=5):
		"""
		Find controls similar to a given control.

		Args:
		    control_id: Control Activity ID
		    limit: Maximum results

		Returns:
		    List of similar controls
		"""
		control = frappe.get_doc("Control Activity", control_id)
		search_text = f"{control.control_name} {control.description or ''}"

		results = self.search(
			query=search_text,
			doctypes=["Control Activity"],
			limit=limit + 1,  # +1 to exclude self
		)

		# Filter out the source control
		return [r for r in results if r["document"] != control_id][:limit]

	def find_related_risks(self, control_id, limit=5):
		"""
		Find risks related to a control based on semantic similarity.

		Args:
		    control_id: Control Activity ID
		    limit: Maximum results

		Returns:
		    List of related risks
		"""
		control = frappe.get_doc("Control Activity", control_id)
		search_text = f"{control.control_name} {control.description or ''} {control.objective or ''}"

		return self.search(query=search_text, doctypes=["Risk Register Entry"], limit=limit)


# API Endpoints
@frappe.whitelist()
def semantic_search(query, doctypes=None, limit=10, threshold=0.5):
	"""
	API endpoint for semantic search.

	Args:
	    query: Search query
	    doctypes: JSON list of DocTypes to search
	    limit: Maximum results
	    threshold: Minimum similarity

	Returns:
	    Search results
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("semantic_search"):
		frappe.throw(_("Semantic search is not enabled"))

	if doctypes and isinstance(doctypes, str):
		doctypes = json.loads(doctypes)

	# Validate user has read permission on all requested DocTypes
	if doctypes:
		for doctype in doctypes:
			if not frappe.has_permission(doctype, "read"):
				frappe.throw(
					_("You do not have permission to search {0}").format(frappe.bold(doctype)),
					frappe.PermissionError,
				)

	search = SemanticSearch()
	return search.search(query=query, doctypes=doctypes, limit=cint(limit), threshold=flt(threshold))


@frappe.whitelist()
def index_document(doctype, docname):
	"""
	API endpoint to index a document.

	Args:
	    doctype: DocType name
	    docname: Document name

	Returns:
	    List of created embedding names
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("semantic_search"):
		frappe.throw(_("Semantic search is not enabled"))

	if not frappe.has_permission(doctype, "read", docname):
		frappe.throw(_("No permission to access {0}").format(doctype))

	search = SemanticSearch()
	return search.index_document(doctype, docname)


@frappe.whitelist()
def rebuild_search_index(doctype=None):
	"""
	API endpoint to rebuild search index.

	Args:
	    doctype: Specific DocType to index (None = all)

	Returns:
	    Indexing summary
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("semantic_search"):
		frappe.throw(_("Semantic search is not enabled"))

	if not frappe.has_permission("Document Embedding", "create"):
		frappe.throw(_("No permission to create embeddings"))

	search = SemanticSearch()
	return search.index_all_documents(doctype)


@frappe.whitelist()
def find_similar_controls(control_id, limit=5):
	"""
	API endpoint to find similar controls.

	Args:
	    control_id: Control Activity ID
	    limit: Maximum results

	Returns:
	    List of similar controls
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("semantic_search"):
		frappe.throw(_("Semantic search is not enabled"))

	if not frappe.has_permission("Control Activity", "read", control_id):
		frappe.throw(_("No permission to access this control"))

	search = SemanticSearch()
	return search.find_similar_controls(control_id, cint(limit))


@frappe.whitelist()
def find_related_risks(control_id, limit=5):
	"""
	API endpoint to find related risks.

	Args:
	    control_id: Control Activity ID
	    limit: Maximum results

	Returns:
	    List of related risks
	"""
	from advanced_compliance.advanced_compliance.doctype.ai_provider_settings.ai_provider_settings import (
		is_ai_feature_enabled,
	)

	if not is_ai_feature_enabled("semantic_search"):
		frappe.throw(_("Semantic search is not enabled"))

	if not frappe.has_permission("Control Activity", "read", control_id):
		frappe.throw(_("No permission to access this control"))

	search = SemanticSearch()
	return search.find_related_risks(control_id, cint(limit))
