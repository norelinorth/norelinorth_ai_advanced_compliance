"""
Dashboard configuration for Risk Register Entry DocType.
"""

from frappe import _


def get_data():
	"""Return dashboard configuration for Risk Register Entry."""
	return {
		"heatmap": True,
		"heatmap_message": _("Risk assessment activity over the past year"),
		"fieldname": "risk",
		"transactions": [{"label": _("Controls"), "items": ["Control Activity"]}],
	}
