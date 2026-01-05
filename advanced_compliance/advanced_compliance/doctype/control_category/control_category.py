"""
Control Category DocType Controller

Hierarchical classification for internal controls.
"""

import frappe
from frappe.utils.nestedset import NestedSet


class ControlCategory(NestedSet):
	"""Controller for Control Category DocType (Tree structure)."""

	nsm_parent_field = "parent_category"
