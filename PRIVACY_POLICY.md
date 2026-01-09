# Privacy Policy

**Effective Date**: January 5, 2026
**Last Updated**: January 5, 2026

## Overview

This Privacy Policy describes how the Noreli North AI Advanced Compliance app ("the App") handles data. **This is not a typical privacy policy** because the App is open source software that runs entirely on your own infrastructure.

## Key Privacy Principles

### 1. No Data Collection by Developer

**The App developer does NOT collect, store, access, or transmit any of your data.**

- No analytics tracking
- No usage statistics
- No phone-home functionality
- No registration required
- No telemetry
- No cookies set by the developer

### 2. Your Data Stays on Your Server

All data created by the App is stored in:
- Your Frappe/ERPNext database (on your server or Frappe Cloud)
- Your file system (for attachments and documents)
- Your server's local storage

The developer has **zero access** to your installation or data.

### 3. You Control Everything

You have complete control over:
- Where your data is stored
- Who has access to your data
- How long data is retained
- Whether to enable optional features
- Data backup and recovery
- Data deletion and purging

## Data Stored by the App

The App stores the following types of data **in your database**:

### Compliance Data
- Control activities and control tests
- Risk register entries and risk assessments
- Test execution results and evidence
- Deficiencies and remediation plans
- COSO principles and framework mappings
- Compliance settings and configurations

### User Activity
- Standard Frappe audit trail (who created/modified records)
- User assignments (control owners, test executors)
- Document comments and notes

### Documents and Files
- Uploaded evidence files (stored in your file system)
- Document attachments (stored per Frappe's file handling)
- Export files (stored temporarily per user request)

### No Sensitive Data Required
The App does **not require** you to store:
- Credit card information
- Social security numbers
- Bank account details
- Passwords (beyond standard Frappe authentication)
- Personal health information

## Optional Third-Party Integrations

The App includes **optional** features that may send data to third parties **only if you explicitly configure and enable them**:

### AI Features (Optional)
If you choose to enable AI features:
- You must configure an AI provider (OpenAI, etc.)
- Data sent: Control descriptions, risk text, compliance documents
- Purpose: Natural language processing, anomaly detection, semantic search
- Privacy: Subject to your chosen AI provider's privacy policy
- Alternative: AI features include rule-based fallbacks that work without external services

### Regulatory Feeds (Optional)
If you choose to enable regulatory feeds:
- The App fetches public regulatory updates from sources like SEC EDGAR, PCAOB
- Data sent: HTTP requests to public regulatory websites
- Data received: Publicly available regulatory filings
- No personal data transmitted

### How to Disable Optional Features
Navigate to **Compliance Settings** and:
- Disable "Enable AI Features"
- Disable "Enable Regulatory Feeds"
- Leave AI Provider Settings empty

## Data Security

### Your Responsibility
Since the App runs on your infrastructure, data security is primarily your responsibility:

- Secure your Frappe/ERPNext installation
- Keep Frappe/ERPNext and the App updated
- Implement proper access controls
- Use HTTPS for web access
- Configure firewall rules
- Perform regular backups
- Follow Frappe's security best practices

### App Security Measures
The App follows security best practices:
- All database queries use parameterized statements (SQL injection prevention)
- Permission checks on all API endpoints
- XSS prevention via proper escaping
- CSRF protection via Frappe's built-in mechanisms
- Audit trail for all changes
- Role-based access control

## Data Retention and Deletion

### Retention
- Data is retained according to your retention policies
- No automatic data purging (you control retention)
- You may configure your own retention rules

### Deletion
To delete data:
- Uninstall the App via `bench --site [site] uninstall-app advanced_compliance`
- This removes all DocTypes and app-specific data
- Standard Frappe/ERPNext data is not affected
- You may also manually delete individual records

## Compliance with Data Protection Laws

### GDPR (European Union)
If you operate in the EU:
- You are the data controller
- The App is a tool you use to process data
- You must ensure your use complies with GDPR
- You can export data, delete data, and exercise all GDPR rights

### CCPA (California)
If you operate in California:
- You control all data collected and stored
- You can provide data access and deletion to individuals
- The App does not "sell" personal information

### Other Regulations
- You are responsible for compliance with laws in your jurisdiction
- The App provides tools to help manage compliance data
- Consult legal counsel for specific regulatory guidance

## Open Source Transparency

The App is **fully open source** (MIT License):
- Source code: https://github.com/norelinorth/norelinorth_ai_advanced_compliance
- You can inspect all code to verify privacy claims
- You can modify the code to meet your privacy requirements
- No hidden functionality or backdoors

## Changes to This Privacy Policy

This Privacy Policy may be updated to reflect:
- Changes in App functionality
- Changes in data handling practices
- Legal or regulatory requirements

Updates will be:
- Documented in GitHub releases
- Posted in the CHANGELOG
- Effective immediately upon publication

## Your Privacy Rights

Because you control the App and your data, you have the right to:
- Access all data stored by the App
- Export data in standard formats
- Delete data at any time
- Modify the App's source code
- Fork the App and create your own version

## Contact

For privacy questions or concerns:
- GitHub Issues: https://github.com/norelinorth/norelinorth_ai_advanced_compliance/issues
- GitHub Discussions: https://github.com/norelinorth/norelinorth_ai_advanced_compliance/discussions

For data privacy issues related to your installation, contact your Frappe/ERPNext administrator.

---

## Summary

**In Plain English:**

1. **We don't collect your data** - The App runs on your server, not ours
2. **You control everything** - All data stays in your database
3. **Open source = transparent** - You can inspect all code
4. **Optional features are optional** - AI and feeds are off by default
5. **Standard Frappe security** - Follows all Frappe best practices
6. **You're the data controller** - You're responsible for compliance with data protection laws

---

**Last Updated**: January 5, 2026
**Version**: 1.0

---

**By using the App, you acknowledge that you have read and understood this Privacy Policy.**
