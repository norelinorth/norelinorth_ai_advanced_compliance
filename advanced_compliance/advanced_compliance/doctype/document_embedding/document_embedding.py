"""
Document Embedding DocType Controller.

Stores vector embeddings for semantic search.
"""

import json

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class DocumentEmbedding(Document):
	"""Controller for Document Embedding DocType."""

	def before_insert(self):
		"""Set creation timestamp."""
		if not self.created_at:
			self.created_at = now_datetime()

	def get_embedding_list(self):
		"""Get embedding vector as a list of floats."""
		if not self.embedding_vector:
			return []
		try:
			return json.loads(self.embedding_vector)
		except (json.JSONDecodeError, TypeError):
			return []

	@staticmethod
	def create_embedding(
		source_doctype, source_document, source_field, embedding_vector, source_text, model_name
	):
		"""
		Create or update a document embedding.

		Args:
		    source_doctype: Source DocType
		    source_document: Source document name
		    source_field: Field that was embedded
		    embedding_vector: List of floats
		    source_text: Original text
		    model_name: Embedding model name

		Returns:
		    Document Embedding document
		"""
		# Check if embedding already exists
		existing = frappe.db.get_value(
			"Document Embedding",
			{
				"source_doctype": source_doctype,
				"source_document": source_document,
				"source_field": source_field,
			},
			"name",
		)

		if existing:
			# Update existing
			doc = frappe.get_doc("Document Embedding", existing)
			doc.embedding_vector = json.dumps(embedding_vector)
			doc.source_text = source_text
			doc.embedding_model = model_name
			doc.created_at = now_datetime()
			doc.save(ignore_permissions=True)
		else:
			# Create new
			doc = frappe.get_doc(
				{
					"doctype": "Document Embedding",
					"source_doctype": source_doctype,
					"source_document": source_document,
					"source_field": source_field,
					"embedding_vector": json.dumps(embedding_vector),
					"source_text": source_text,
					"embedding_model": model_name,
				}
			)
			doc.insert(ignore_permissions=True)

		return doc

	@staticmethod
	def get_embedding(source_doctype, source_document, source_field):
		"""
		Get embedding for a specific document field.

		Args:
		    source_doctype: Source DocType
		    source_document: Source document name
		    source_field: Field that was embedded

		Returns:
		    Document Embedding or None
		"""
		name = frappe.db.get_value(
			"Document Embedding",
			{
				"source_doctype": source_doctype,
				"source_document": source_document,
				"source_field": source_field,
			},
			"name",
		)

		if name:
			return frappe.get_doc("Document Embedding", name)
		return None

	@staticmethod
	def delete_for_document(source_doctype, source_document):
		"""Delete all embeddings for a document."""
		frappe.db.delete(
			"Document Embedding", {"source_doctype": source_doctype, "source_document": source_document}
		)

	@staticmethod
	def get_all_embeddings(source_doctype=None, limit=1000):
		"""
		Get all embeddings, optionally filtered by DocType.

		Args:
		    source_doctype: Optional filter by DocType
		    limit: Maximum embeddings to return

		Returns:
		    List of embedding documents
		"""
		filters = {}
		if source_doctype:
			filters["source_doctype"] = source_doctype

		return frappe.get_all(
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
			limit=limit,
		)
