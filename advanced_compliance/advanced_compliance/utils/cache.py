# Copyright (c) 2024, Noreli North and contributors
# For license information, please see license.txt

"""
Caching utilities for Advanced Compliance

Provides Redis-based caching for expensive operations.
"""

import json

import frappe
from frappe import _

CACHE_PREFIX = "advanced_compliance:"
DEFAULT_TTL = 3600  # 1 hour


def get_cached(key, generator_func, ttl=DEFAULT_TTL):
	"""
	Get value from cache or generate and cache it.

	Args:
		key: Cache key
		generator_func: Function to generate value if not cached
		ttl: Time to live in seconds

	Returns:
		Cached or generated value
	"""
	cache_key = f"{CACHE_PREFIX}{key}"
	cached = frappe.cache().get_value(cache_key)

	if cached is not None:
		try:
			return json.loads(cached) if isinstance(cached, str) else cached
		except (json.JSONDecodeError, TypeError):
			return cached

	value = generator_func()
	try:
		frappe.cache().set_value(cache_key, json.dumps(value), expires_in_sec=ttl)
	except (TypeError, ValueError):
		# Value not JSON serializable, cache as-is
		frappe.cache().set_value(cache_key, value, expires_in_sec=ttl)

	return value


def invalidate_cache(pattern):
	"""
	Invalidate cache keys matching pattern.

	Args:
		pattern: Pattern to match (without prefix). If exact key, deletes that key.
	"""
	try:
		cache_key = f"{CACHE_PREFIX}{pattern}"
		# Try to delete exact key first
		frappe.cache().delete_value(cache_key)
		# Then delete pattern matches
		frappe.cache().delete_keys(f"{cache_key}*")
	except Exception as e:
		# Log cache errors but don't fail the operation
		frappe.log_error(
			message=f"Cache invalidation error for pattern '{pattern}': {str(e)}",
			title="Compliance Cache Error",
		)


def get_graph_cache_key(entity_type, entity_name):
	"""
	Generate cache key for graph queries.

	Args:
		entity_type: Entity DocType
		entity_name: Entity document name

	Returns:
		str: Cache key
	"""
	return f"graph:{entity_type}:{entity_name}"


def clear_all_compliance_cache():
	"""Clear all Advanced Compliance caches."""
	invalidate_cache("")


# Cache invalidation hooks for doc_events
def on_control_change(doc, method):
	"""Invalidate control-related caches on change."""
	invalidate_cache("dashboard")
	invalidate_cache(f"graph:Control Activity:{doc.name}")
	invalidate_cache("controls_list")
	invalidate_cache("compliance_summary")


def on_risk_change(doc, method):
	"""Invalidate risk-related caches on change."""
	invalidate_cache("dashboard")
	invalidate_cache("risk_heatmap")
	invalidate_cache(f"graph:Risk Register Entry:{doc.name}")
	invalidate_cache("compliance_summary")


def on_test_change(doc, method):
	"""Invalidate test-related caches on change."""
	invalidate_cache("dashboard")
	invalidate_cache("compliance_summary")
	if doc.control:
		invalidate_cache(f"control_stats:{doc.control}")


def on_deficiency_change(doc, method):
	"""Invalidate deficiency-related caches on change."""
	invalidate_cache("dashboard")
	invalidate_cache("compliance_summary")
	if doc.control:
		invalidate_cache(f"control_stats:{doc.control}")


def on_regulatory_update_change(doc, method):
	"""Invalidate regulatory-related caches on change."""
	invalidate_cache("dashboard")
	invalidate_cache("regulatory_timeline")
	invalidate_cache("compliance_summary")
