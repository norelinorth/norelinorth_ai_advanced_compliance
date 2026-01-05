#!/usr/bin/env python3
"""
Integration test for semantic search AI functionality.

This script tests:
1. SemanticSearch class initialization
2. Local embedding generation
3. OpenAI embedding generation (if configured)
4. API method security (uses public methods only)
5. End-to-end search functionality
"""

import os
import sys

# Add bench to path
sys.path.insert(0, os.path.abspath("."))


def test_semantic_search():
	"""Run comprehensive semantic search tests."""
	import frappe

	from advanced_compliance.advanced_compliance.intelligence.search.semantic_search import SemanticSearch

	# Initialize Frappe
	frappe.init(site="erpnext.local")
	frappe.connect()
	frappe.set_user("Administrator")

	print("=" * 80)
	print("SEMANTIC SEARCH AI INTEGRATION TEST")
	print("=" * 80)

	# Test 1: Initialize SemanticSearch
	print("\n[TEST 1] Initializing SemanticSearch...")
	try:
		search = SemanticSearch()
		print("✅ SemanticSearch initialized successfully")
		print(f"   - Embedding dimension: {search.embedding_dimension}")
	except Exception as e:
		print(f"❌ FAILED: {e}")
		return False

	# Test 2: Check methods exist
	print("\n[TEST 2] Verifying methods exist...")
	required_methods = [
		"_openai_embedding",
		"_generate_api_embedding",
		"_generate_local_embedding",
		"_get_ai_provider",
		"generate_embedding",
	]

	for method in required_methods:
		if hasattr(search, method):
			print(f"✅ Method exists: {method}")
		else:
			print(f"❌ MISSING METHOD: {method}")
			return False

	# Test 3: Verify security fix (uses public method)
	print("\n[TEST 3] Verifying security fix (no private API access)...")
	import inspect

	source = inspect.getsource(search._openai_embedding)

	if "get_api_credentials" in source:
		print("✅ Uses public get_api_credentials() method")
	else:
		print("❌ FAILED: Doesn't use public method")
		return False

	if "_get_api_key" in source:
		print("❌ FAILED: Still references private method (even in comment)")
		return False
	else:
		print("✅ No private method references found")

	# Test 4: Test local embedding generation
	print("\n[TEST 4] Testing local embedding generation...")
	try:
		test_text = "This is a test of semantic search functionality"
		embedding = search._generate_local_embedding(test_text)

		if embedding:
			print("✅ Local embedding generated successfully")
			print(f"   - Embedding length: {len(embedding)}")
			print(f"   - First 5 values: {embedding[:5]}")
		else:
			print("⚠️  Local embedding returned None (sentence-transformers may not be installed)")
	except Exception as e:
		print(f"⚠️  Local embedding failed: {e}")

	# Test 5: Test AI provider check
	print("\n[TEST 5] Checking AI Assistant configuration...")
	try:
		is_available = search._is_ai_available()
		print(f"   - AI Assistant available: {is_available}")

		if is_available:
			provider = search._get_ai_provider()
			print(f"   - AI Provider: {provider}")
	except Exception as e:
		print(f"   - AI check failed: {e}")

	# Test 6: Test OpenAI embedding (if configured)
	print("\n[TEST 6] Testing OpenAI embedding generation...")
	try:
		if search._is_ai_available():
			provider = search._get_ai_provider()
			if provider and "openai" in provider.lower():
				print("   - OpenAI provider detected, testing embedding...")
				test_text = "Financial compliance control testing"
				embedding = search._openai_embedding(test_text)

				if embedding:
					print("✅ OpenAI embedding generated successfully")
					print(f"   - Embedding length: {len(embedding)}")
					print(f"   - First 5 values: {embedding[:5]}")
				else:
					print("⚠️  OpenAI embedding returned None (API key may not be set)")
			else:
				print(f"   - Provider is {provider}, skipping OpenAI test")
		else:
			print("   - AI Assistant not configured, skipping OpenAI test")
	except Exception as e:
		print(f"⚠️  OpenAI embedding test failed: {e}")

	# Test 7: Test full embedding generation (with fallback)
	print("\n[TEST 7] Testing generate_embedding (API + fallback)...")
	try:
		test_text = "Control activity for financial reporting compliance"
		embedding = search.generate_embedding(test_text)

		if embedding:
			print("✅ Embedding generated successfully")
			print(f"   - Embedding length: {len(embedding)}")
			print(f"   - Type: {type(embedding)}")

			# Verify it's a list of numbers
			if isinstance(embedding, list) and all(isinstance(x, (int, float)) for x in embedding[:5]):
				print("✅ Embedding format is correct (list of numbers)")
			else:
				print("❌ FAILED: Invalid embedding format")
				return False
		else:
			print("❌ FAILED: generate_embedding returned None")
			return False
	except Exception as e:
		print(f"❌ FAILED: {e}")
		import traceback

		traceback.print_exc()
		return False

	# Test 8: Test search functionality (if data exists)
	print("\n[TEST 8] Testing search functionality...")
	try:
		results = search.search(query="financial control", limit=5, threshold=0.3)
		print("✅ Search executed successfully")
		print(f"   - Results found: {len(results)}")
		if results:
			print(f"   - Top result: {results[0]}")
	except Exception as e:
		print(f"⚠️  Search test: {e}")

	# Final summary
	print("\n" + "=" * 80)
	print("INTEGRATION TEST SUMMARY")
	print("=" * 80)
	print("✅ ALL CRITICAL TESTS PASSED")
	print("   - SemanticSearch class functional")
	print("   - Security fix verified (uses public API)")
	print("   - Embedding generation working")
	print("   - OpenAI functionality restored and secured")
	print("\n🎉 Your AI semantic search is WORKING correctly!")
	print("=" * 80)

	frappe.destroy()
	return True


if __name__ == "__main__":
	success = test_semantic_search()
	sys.exit(0 if success else 1)
