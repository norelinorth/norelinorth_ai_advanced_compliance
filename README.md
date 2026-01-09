# Noreli North Advanced Compliance

**Next-Generation GRC (Governance, Risk, Compliance) for Frappe/ERPNext**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Frappe Version](https://img.shields.io/badge/Frappe-v15-blue)](https://frappeframework.com)
[![ERPNext Version](https://img.shields.io/badge/ERPNext-v15-blue)](https://erpnext.com)
[![Tests](https://img.shields.io/badge/Tests-225%20Passing-green)](.)

## Overview

Transform compliance from a periodic checkbox exercise into a continuous, intelligent, and proactive business capability. Noreli North Advanced Compliance is a comprehensive GRC solution built natively on Frappe/ERPNext.

## Key Features

### Control Management
- **Control Catalog** - Comprehensive control library with COSO framework alignment
- **Control Testing** - Structured test execution with evidence capture
- **Deficiency Tracking** - Issue identification through remediation

### Risk Management
- **Risk Register** - Full risk assessment with inherent/residual scoring
- **Risk Categories** - Hierarchical risk classification
- **Risk-Control Mapping** - Link controls to risks they mitigate

### Knowledge Graph Engine
- **Relationship Intelligence** - Visualize connections between controls, risks, and entities
- **Impact Analysis** - Understand downstream effects of changes
- **Coverage Analysis** - Identify gaps in control coverage

### AI Intelligence (Optional)
- **Anomaly Detection** - Identify unusual patterns in compliance data
- **Natural Language Queries** - Ask questions in plain English
- **Risk Prediction** - ML-based control failure probability
- **Auto-Suggestions** - Intelligent recommendations for improvements

### Evidence Management
- **Automated Capture** - Rule-based evidence collection from ERPNext
- **Document Linking** - Attach files to controls and tests
- **Audit Trail** - Complete history of all compliance activities

## Supported Frameworks

- SOX Section 404 (Primary)
- COSO Internal Control Framework (17 Principles)
- COBIT 2019
- ISO 27001
- GDPR
- Industry-specific (FDA, HIPAA, PCI-DSS)

## Installation

### From Frappe Cloud
1. Go to your Frappe Cloud dashboard
2. Navigate to Apps
3. Search for "Noreli North Advanced Compliance"
4. Click Install

### Manual Installation

```bash
# Get the app
bench get-app https://github.com/norelinorth/advanced_compliance.git

# Install on your site
bench --site your-site.local install-app advanced_compliance

# Run migrations
bench --site your-site.local migrate
```

## Requirements

- Frappe Framework v15.0.0+
- ERPNext v15.0.0+
- Python 3.10+
- MariaDB 10.6+ or PostgreSQL 14+

## Configuration

### Quick Start

1. Navigate to **Compliance Workspace** in the sidebar
2. Configure **Compliance Settings** with your company details
3. Create **Control Categories** to organize your controls
4. Create **Risk Categories** for risk classification
5. Start adding **Control Activities** and **Risk Register Entries**

### AI Features (Optional)

1. Configure **AI Provider Settings** with your API keys
2. Enable desired AI features (anomaly detection, NL queries, etc.)
3. AI features work without external providers using rule-based fallbacks

## Demo Data

Generate sample Finance & Accounting compliance data for testing:

```bash
bench --site your-site.local execute "advanced_compliance.advanced_compliance.demo.finance_accounting_data.setup_finance_accounting_data"
```

This creates:
- 20 SOX-style control activities
- 12 financial risk register entries
- 17 COSO principles
- Control and risk categories

## Data Import/Export

Export your compliance data:
```bash
bench --site your-site.local execute "advanced_compliance.advanced_compliance.utils.data_exchange.export_compliance_data"
```

## DocTypes

| DocType | Description |
|---------|-------------|
| Control Activity | Internal control definitions |
| Control Category | Control classification hierarchy |
| Risk Register Entry | Organizational risks |
| Risk Category | Risk classification hierarchy |
| Test Execution | Control testing documentation |
| Deficiency | Control weaknesses and remediation |
| COSO Principle | COSO framework principles |
| Compliance Framework | Framework definitions |
| Framework Requirement | Framework-specific requirements |
| Evidence Capture Rule | Automated evidence collection rules |

## API Endpoints

All API endpoints are accessible via `/api/method/advanced_compliance.advanced_compliance...`

### Knowledge Graph
- `get_entity_details` - Get entity with relationships
- `get_entity_relationships` - Get relationships for an entity
- `get_compliance_score` - Calculate compliance coverage score
- `get_coverage_analysis` - Full coverage gap analysis

### AI Intelligence
- `predict_control_risk` - Predict control failure probability
- `get_control_suggestions` - Get control recommendations
- `detect_compliance_anomalies` - Run anomaly detection

## Roles and Permissions

| Role | Access Level |
|------|--------------|
| Compliance Admin | Full access to all features |
| Compliance Officer | Manage controls, risks, testing |
| Internal Auditor | Execute tests, review deficiencies |
| Control Owner | Update assigned controls |
| Compliance Viewer | Read-only access |

## Test Coverage

- **225 tests** (224 passing, 1 skipped) covering all major functionality
- Unit tests for business logic
- Integration tests for workflows
- API endpoint tests
- 43% code coverage with 100% coverage of critical business logic

Run tests:
```bash
bench --site your-site.local run-tests --app advanced_compliance
```

## Support

- **Documentation**: [GitHub Wiki](https://github.com/norelinorth/advanced_compliance/wiki)
- **Bug Reports & Feature Requests**: [Raise an Issue](https://github.com/norelinorth/advanced_compliance/issues)
- **Discussions**: [GitHub Discussions](https://github.com/norelinorth/advanced_compliance/discussions)

## License

MIT License - See [LICENSE](./license.txt) for details

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

---

**Noreli North Advanced Compliance** - Intelligent compliance management for ERPNext

*Built with Frappe Framework*
