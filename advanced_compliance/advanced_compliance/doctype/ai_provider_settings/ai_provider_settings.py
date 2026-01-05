"""
AI Provider Settings DocType Controller.

Single DocType for configuring AI/ML features in the compliance app.
AI Provider configuration is managed centrally via the AI Assistant app.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class AIProviderSettings(Document):
	"""Controller for AI Provider Settings."""

	def validate(self):
		"""Validate settings."""
		self.validate_thresholds()

	def validate_thresholds(self):
		"""Validate threshold values are in valid range."""
		if self.high_risk_threshold:
			threshold = flt(self.high_risk_threshold)
			if threshold < 0 or threshold > 1:
				frappe.throw(_("High Risk Threshold must be between 0.0 and 1.0"))

		if self.critical_risk_threshold:
			threshold = flt(self.critical_risk_threshold)
			if threshold < 0 or threshold > 1:
				frappe.throw(_("Critical Risk Threshold must be between 0.0 and 1.0"))

		if self.high_risk_threshold and self.critical_risk_threshold:
			if flt(self.high_risk_threshold) >= flt(self.critical_risk_threshold):
				frappe.throw(_("High Risk Threshold must be less than Critical Risk Threshold"))

	def is_feature_enabled(self, feature):
		"""Check if a specific feature is enabled."""
		feature_map = {
			"risk_prediction": self.enable_risk_prediction,
			"anomaly_detection": self.enable_anomaly_detection,
			"nl_queries": self.enable_nl_queries,
			"natural_language_queries": self.enable_nl_queries,
			"semantic_search": self.enable_semantic_search,
			"suggestions": self.enable_suggestions,
			"auto_suggestions": self.enable_suggestions,
		}
		return bool(feature_map.get(feature, False))

	def get_anomaly_sensitivity_value(self):
		"""
		Get numeric value for anomaly sensitivity.

		Returns:
		    float: Sensitivity multiplier (0.5 = Low, 1.0 = Medium, 2.0 = High)
		           Returns 1.0 (Medium) if not configured.
		"""
		sensitivity_map = {"Low": 0.5, "Medium": 1.0, "High": 2.0}

		# Return default if not configured (don't throw from getter)
		if not self.anomaly_sensitivity or self.anomaly_sensitivity not in sensitivity_map:
			return 1.0  # Default to Medium sensitivity

		return sensitivity_map[self.anomaly_sensitivity]

	def get_risk_level(self, probability):
		"""Get risk level string based on probability."""
		probability = flt(probability)
		critical_threshold = flt(self.critical_risk_threshold)
		high_threshold = flt(self.high_risk_threshold)

		if not critical_threshold or not high_threshold:
			frappe.throw(_("Please configure Risk Thresholds in AI Provider Settings"))

		if probability >= critical_threshold:
			return _("Critical")
		elif probability >= high_threshold:
			return _("High")
		elif probability >= 0.4:
			return _("Medium")
		else:
			return _("Low")


def get_ai_settings():
	"""
	Get AI Provider Settings singleton.

	Returns:
	    AIProviderSettings document
	"""
	return frappe.get_single("AI Provider Settings")


def is_ai_feature_enabled(feature):
	"""
	Check if a specific AI feature is enabled.

	Args:
	    feature: One of 'risk_prediction', 'anomaly_detection',
	            'nl_queries', 'semantic_search', 'suggestions'

	Returns:
	    bool
	"""
	settings = get_ai_settings()
	return settings.is_feature_enabled(feature)


def is_ai_assistant_available():
	"""
	Check if the AI Assistant app is installed and configured.

	Returns:
	    bool: True if AI Assistant is available and configured
	"""
	try:
		# Check if app is installed
		if "norelinorth_ai_assistant" not in frappe.get_installed_apps():
			return False

		# Check if AI Provider is configured
		from norelinorth_ai_assistant.ai_provider_resolver import AIProviderResolver

		config = AIProviderResolver.get_ai_provider_config()

		return config.get("is_active", False) and config.get("api_key_status") == "SET"
	except Exception:
		return False


def get_ai_provider_config():
	"""
	Get AI Provider configuration from AI Assistant app.

	Returns:
	    dict with provider configuration or None if not available
	"""
	try:
		from norelinorth_ai_assistant.ai_provider_resolver import AIProviderResolver

		return AIProviderResolver.get_ai_provider_config()
	except ImportError:
		frappe.log_error(message="AI Assistant app is not installed", title=_("AI Provider Error"))
		return None
	except Exception as e:
		frappe.log_error(message=f"Failed to get AI Provider config: {str(e)}", title=_("AI Provider Error"))
		return None


def call_llm(prompt, context=None, system_message=None):
	"""
	Call the LLM using the centralized AI Assistant app.

	This function provides a simple interface for all compliance AI features
	to call the LLM without managing their own API clients.

	Args:
	    prompt: The user prompt/question
	    context: Optional context dictionary
	    system_message: Optional system message override

	Returns:
	    str: LLM response text, or error message if failed
	"""
	try:
		# Check if AI Assistant is available
		if not is_ai_assistant_available():
			return _("AI Provider is not configured. Please configure it in AI Provider settings.")

		# Use AI Assistant's resolver
		from norelinorth_ai_assistant.ai_provider_resolver import AIProviderResolver

		response = AIProviderResolver.call_ai_api(
			prompt=prompt, context=context, system_message=system_message
		)

		return response

	except ImportError:
		return _("AI Assistant app is required for AI features. Please install norelinorth_ai_assistant.")
	except frappe.PermissionError:
		return _("Insufficient permissions to use AI features.")
	except Exception as e:
		frappe.log_error(
			message=f"LLM Call Error: {str(e)}\n{frappe.get_traceback()}", title="AI Provider Error"
		)
		return _("AI analysis failed. Please check Error Log for details.")


def get_llm_client():
	"""
	DEPRECATED: Use call_llm() instead.

	This function is kept for backwards compatibility but now returns
	a wrapper that uses the AI Assistant app.

	Returns:
	    AIClientWrapper or None
	"""
	if not is_ai_assistant_available():
		return None

	return AIClientWrapper()


class AIClientWrapper:
	"""
	Wrapper class for backwards compatibility.

	Provides a simple interface that mimics the old direct client usage
	but delegates to the AI Assistant app.
	"""

	def __init__(self):
		self.available = is_ai_assistant_available()

	def create_completion(self, prompt, system_message=None):
		"""
		Create a completion using the AI Assistant app.

		Args:
		    prompt: The prompt text
		    system_message: Optional system message

		Returns:
		    str: Response text
		"""
		return call_llm(prompt, system_message=system_message)

	def chat(self, messages):
		"""
		Send chat messages using the AI Assistant app.

		Args:
		    messages: List of message dicts with 'role' and 'content'

		Returns:
		    str: Response text
		"""
		# Extract the last user message as prompt
		user_messages = [m for m in messages if m.get("role") == "user"]
		system_messages = [m for m in messages if m.get("role") == "system"]

		prompt = user_messages[-1]["content"] if user_messages and len(user_messages) > 0 else ""
		system_message = (
			system_messages[0]["content"] if system_messages and len(system_messages) > 0 else None
		)

		return call_llm(prompt, system_message=system_message)
