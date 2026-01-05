"""
Risk Category DocType Controller

Hierarchical classification for risks.
"""

import frappe
from frappe.utils.nestedset import NestedSet


class RiskCategory(NestedSet):
	"""Controller for Risk Category DocType (Tree structure)."""

	nsm_parent_field = "parent_category"
