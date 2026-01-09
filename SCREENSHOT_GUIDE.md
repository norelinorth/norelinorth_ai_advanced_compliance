# Screenshot Guide for Frappe Marketplace

This guide explains how to capture professional screenshots for the Frappe Marketplace listing.

## Screenshot Requirements

- **Minimum**: 3 screenshots
- **Recommended**: 6-8 screenshots
- **Format**: PNG or JPG
- **Resolution**: Minimum 1280x720, recommended 1920x1080
- **Aspect Ratio**: 16:9 preferred
- **File Size**: Under 5MB per image

---

## Required Screenshots

### 1. Compliance Workspace Dashboard (REQUIRED)
**Filename**: `01_workspace_dashboard.png`

**What to show**:
- Main Compliance Workspace with all shortcuts visible
- Professional, clean layout
- Key metrics at a glance

**How to capture**:
1. Navigate to **Compliance** workspace
2. Ensure you're logged in as Compliance Admin
3. Show the full workspace with all cards
4. Capture full screen at 1920x1080

**Sample data**: Use demo data if available

---

### 2. Control Activity Form (REQUIRED)
**Filename**: `02_control_activity_form.png`

**What to show**:
- A well-populated Control Activity document
- All key fields visible (Control ID, Description, COSO Principle, Owner, etc.)
- Professional formatting

**How to capture**:
1. Open an existing Control Activity (or create one with demo data)
2. Populate all fields with realistic data
3. Scroll to show important sections
4. Capture the form view

**Example data**:
```
Control ID: AC-001
Title: Journal Entry Review and Approval
Control Type: Preventive
COSO Principle: Control Activities
Control Owner: Jane Doe, Controller
Test Frequency: Monthly
Description: All manual journal entries must be reviewed and approved by the Controller before posting...
```

---

### 3. Risk Register with Heat Map (REQUIRED)
**Filename**: `03_risk_register_heatmap.png`

**What to show**:
- Risk Register Entry with scoring
- Visual heat map or risk matrix
- Inherent vs Residual risk scores

**How to capture**:
1. Open a Risk Register Entry with complete scoring
2. Show risk heat map if available
3. Capture risk details and controls mapped

**Example data**:
```
Risk ID: RISK-001
Risk Title: Unauthorized Journal Entry Posting
Category: Financial Reporting
Inherent Risk: High (Impact: 5, Likelihood: 4)
Residual Risk: Medium (Impact: 5, Likelihood: 2)
Mitigating Controls: AC-001, AC-002
```

---

### 4. Knowledge Graph Visualization (OPTIONAL but IMPRESSIVE)
**Filename**: `04_knowledge_graph.png`

**What to show**:
- Interactive knowledge graph page
- Relationships between controls, risks, and entities
- Network visualization with nodes and edges

**How to capture**:
1. Navigate to Knowledge Graph page
2. Select an entity (Control, Risk, or Person)
3. Show the relationship network
4. Capture with visible connections

---

### 5. Test Execution Workflow (RECOMMENDED)
**Filename**: `05_test_execution.png`

**What to show**:
- Test Execution form with results
- Evidence attachments
- Pass/Fail status
- Deficiency identification if applicable

**How to capture**:
1. Open a Test Execution document
2. Show completed test with evidence
3. Display attachments section
4. Capture full form

**Example data**:
```
Test Execution: TEST-2026-001
Control: AC-001 (Journal Entry Review)
Test Date: 2026-01-05
Tester: John Smith, Internal Auditor
Result: Pass
Evidence: 20 sample journal entries reviewed, all approved
Attachments: approval_signatures.pdf
```

---

### 6. Compliance Coverage Analysis (RECOMMENDED)
**Filename**: `06_coverage_analysis.png`

**What to show**:
- Coverage analysis report or dashboard
- Gap analysis metrics
- Control coverage by category/framework

**How to capture**:
1. Navigate to Compliance Reports
2. Run Coverage Analysis report
3. Show metrics and gaps
4. Capture full report view

---

### 7. AI Query Interface (OPTIONAL)
**Filename**: `07_ai_queries.png`

**What to show**:
- Natural language query interface
- Example query and results
- Semantic search in action

**How to capture**:
1. If AI features are enabled, navigate to AI Query page
2. Enter a sample query: "Show me all controls related to financial reporting"
3. Display intelligent results
4. Capture query and response

---

### 8. Regulatory Feed Dashboard (OPTIONAL)
**Filename**: `08_regulatory_feeds.png`

**What to show**:
- List of regulatory feed sources
- Recent updates from SEC, PCAOB, etc.
- Sync status and impact mapping

**How to capture**:
1. Navigate to Regulatory Feed Sources
2. Show configured feeds with last sync time
3. Display recent regulatory updates
4. Capture list view with details

---

## Screenshot Best Practices

### Before Capturing

1. **Clean Browser**:
   - Close unnecessary browser tabs
   - Use incognito mode to avoid extensions
   - Clear any notification banners

2. **Sample Data**:
   - Use realistic, professional data
   - Populate all fields (no "Test 1", "Test 2")
   - Use proper business terminology
   - Ensure dates are current

3. **User Interface**:
   - Full screen browser (F11)
   - Remove developer tools if open
   - Hide personal information
   - Use a clean theme (standard ERPNext theme)

### During Capture

1. **Resolution**:
   - Capture at 1920x1080 (Full HD)
   - Use browser zoom at 100%
   - Ensure text is readable

2. **Framing**:
   - Include navigation bar at top
   - Show full form without scrolling if possible
   - Center important content
   - Avoid cutting off labels or buttons

3. **Content**:
   - Show 3-5 records in list views (not empty, not too crowded)
   - Display meaningful data in all visible fields
   - Highlight key features naturally (no annotation needed)

### After Capture

1. **Image Editing** (optional):
   - Crop to remove unnecessary browser chrome
   - Add subtle drop shadow if desired
   - Annotate key features with arrows/boxes (optional)
   - Blur any sensitive data if using production screenshots

2. **File Optimization**:
   - Save as PNG for UI screenshots (lossless)
   - Compress to under 5MB if needed
   - Name files consistently (01_*, 02_*, etc.)

3. **Review**:
   - Check for typos in visible text
   - Verify no personal/sensitive data visible
   - Ensure screenshot tells a story
   - Test readability at smaller sizes

---

## Tools for Capturing Screenshots

### Built-in Tools
- **macOS**: Cmd+Shift+4 (selection), Cmd+Shift+3 (full screen)
- **Windows**: Snipping Tool, Win+Shift+S
- **Linux**: Flameshot, Spectacle, gnome-screenshot

### Professional Tools
- **Snagit** (paid): Advanced capture and annotation
- **Greenshot** (free): Windows screenshot tool with editing
- **Ksnip** (free): Cross-platform with annotation
- **Monosnap** (free): Simple capture with basic editing

---

## Suggested Screenshot Sequence

For optimal marketplace presentation, arrange screenshots in this order:

1. **Overview First**: Workspace Dashboard (shows everything at a glance)
2. **Core Features**: Control Activity, Risk Register (primary use cases)
3. **Workflows**: Test Execution (how users work with the app)
4. **Advanced Features**: Knowledge Graph, AI Queries (differentiators)
5. **Integrations**: Regulatory Feeds (value-adds)
6. **Reports**: Coverage Analysis (business value)

---

## Demo Data Setup

Before capturing screenshots, populate demo data:

```bash
# SSH into your Frappe bench
cd ~/frappe-bench

# Run demo data generator
bench --site erpnext.local execute "advanced_compliance.advanced_compliance.demo.finance_accounting_data.setup_finance_accounting_data"

# This creates:
# - 20 SOX-style control activities
# - 12 financial risk register entries
# - 17 COSO principles
# - Control and risk categories
# - Sample test executions
```

---

## Quality Checklist

Before uploading screenshots:

- [ ] All screenshots at 1920x1080 or higher
- [ ] Realistic, professional sample data
- [ ] No personal information visible
- [ ] No typos in visible text
- [ ] Clean browser UI (no clutter)
- [ ] Consistent theme across all screenshots
- [ ] All images under 5MB
- [ ] Files named sequentially (01_*, 02_*, etc.)
- [ ] At least 3 screenshots prepared
- [ ] Each screenshot tells a clear story

---

## Need Help?

If you need assistance capturing screenshots:
- GitHub Issues: https://github.com/norelinorth/advanced_compliance/issues
- Ask in Discussions: https://github.com/norelinorth/advanced_compliance/discussions

---

**Last Updated**: January 9, 2026
