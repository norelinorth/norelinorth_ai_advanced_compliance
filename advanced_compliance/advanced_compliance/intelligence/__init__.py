"""
Intelligence Module.

AI/ML features for compliance analysis including:
- Risk prediction for controls
- Compliance anomaly detection
- Natural language queries
- Semantic search
- Auto-suggestions
"""

from advanced_compliance.advanced_compliance.intelligence.anomaly.compliance_anomaly import (
	ComplianceAnomalyDetector,
)
from advanced_compliance.advanced_compliance.intelligence.nlp.query_engine import NLQueryEngine
from advanced_compliance.advanced_compliance.intelligence.prediction.risk_predictor import RiskPredictor
from advanced_compliance.advanced_compliance.intelligence.search.semantic_search import SemanticSearch
from advanced_compliance.advanced_compliance.intelligence.suggestions.auto_suggest import AutoSuggest

__all__ = ["RiskPredictor", "ComplianceAnomalyDetector", "NLQueryEngine", "SemanticSearch", "AutoSuggest"]
