"""
Dashboard configuration for Control Activity DocType.
"""

from frappe import _


def get_data():
	"""Return dashboard configuration for Control Activity."""
	return {
		"heatmap": True,
		"heatmap_message": _("Testing activity over the past year"),
		"fieldname": "control",
		"transactions": [
			{"label": _("Testing"), "items": ["Test Execution"]},
			{"label": _("Deficiencies"), "items": ["Deficiency"]},
			{"label": _("Evidence"), "items": ["Control Evidence"]},
			{"label": _("AI Predictions"), "items": ["Risk Prediction"]},
		],
	}
