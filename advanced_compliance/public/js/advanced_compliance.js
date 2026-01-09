/*
 * Advanced Compliance - Main JavaScript
 * Client-side functionality and utilities
 */

frappe.provide("advanced_compliance");

advanced_compliance = {
  /**
   * Initialize the Advanced Compliance module
   */
  init: function () {
    this.setup_realtime_updates();
    this.setup_keyboard_shortcuts();

    if (this.is_mobile()) {
      this.setup_mobile_handlers();
    }
  },

  /**
   * Check if device is mobile
   */
  is_mobile: function () {
    return window.innerWidth <= 768 || "ontouchstart" in window;
  },

  /**
   * Setup real-time updates for dashboard
   */
  setup_realtime_updates: function () {
    // Listen for compliance-related updates
    frappe.realtime.on("compliance_update", function (data) {
      if (data.doctype === "Deficiency" && data.status === "new") {
        frappe.show_alert(
          {
            message: __("New deficiency created: {0}", [data.name]),
            indicator: "red",
          },
          5,
        );
      }

      if (data.doctype === "Regulatory Update" && data.status === "new") {
        frappe.show_alert(
          {
            message: __("New regulatory update: {0}", [data.title]),
            indicator: "blue",
          },
          5,
        );
      }
    });
  },

  /**
   * Setup keyboard shortcuts
   */
  setup_keyboard_shortcuts: function () {
    var self = this;

    // Alt+C - Go to Control Activity list
    frappe.ui.keys.add_shortcut({
      shortcut: "alt+c",
      action: function () {
        frappe.set_route("List", "Control Activity");
      },
      description: __("Go to Control Activities"),
    });

    // Alt+R - Go to Risk Register
    frappe.ui.keys.add_shortcut({
      shortcut: "alt+r",
      action: function () {
        frappe.set_route("List", "Risk Register Entry");
      },
      description: __("Go to Risk Register"),
    });

    // Alt+T - Go to Test Executions
    frappe.ui.keys.add_shortcut({
      shortcut: "alt+t",
      action: function () {
        frappe.set_route("List", "Test Execution");
      },
      description: __("Go to Test Executions"),
    });

    // Alt+D - Go to Dashboard
    frappe.ui.keys.add_shortcut({
      shortcut: "alt+d",
      action: function () {
        frappe.set_route("Workspaces", "Advanced Compliance");
      },
      description: __("Go to Compliance Dashboard"),
    });

    // Alt+Q - Open NL Query Dialog
    frappe.ui.keys.add_shortcut({
      shortcut: "alt+q",
      action: function () {
        self.show_nl_query_dialog();
      },
      description: __("Ask Compliance Question"),
    });
  },

  /**
   * Setup mobile-specific handlers
   */
  setup_mobile_handlers: function () {
    // Increase touch target sizes
    document.querySelectorAll(".frappe-control").forEach(function (el) {
      el.style.minHeight = "44px";
    });
  },

  /**
   * Format risk score for display
   * @param {number} score - Risk score (1-25)
   * @returns {object} - Score with color and label
   */
  format_risk_score: function (score) {
    score = parseFloat(score) || 0;

    if (score >= 20) {
      return { score: score, color: "red", label: __("Critical") };
    } else if (score >= 15) {
      return { score: score, color: "orange", label: __("High") };
    } else if (score >= 10) {
      return { score: score, color: "yellow", label: __("Medium") };
    } else if (score >= 5) {
      return { score: score, color: "blue", label: __("Low") };
    } else {
      return { score: score, color: "green", label: __("Very Low") };
    }
  },

  /**
   * Create risk heatmap
   * @param {HTMLElement} container - Container element
   * @param {Array} data - Risk data
   */
  render_risk_heatmap: function (container, data) {
    var self = this;
    var html = '<table class="table table-bordered">';

    // Header row
    html += "<thead><tr><th></th>";
    for (var i = 1; i <= 5; i++) {
      html += '<th class="text-center">Impact ' + i + "</th>";
    }
    html += "</tr></thead>";

    // Data rows
    html += "<tbody>";
    for (var likelihood = 5; likelihood >= 1; likelihood--) {
      html += "<tr>";
      html += "<th>Likelihood " + likelihood + "</th>";

      for (var impact = 1; impact <= 5; impact++) {
        var score = impact * likelihood;
        var cell_data = data.find(function (d) {
          return d.impact_rating == impact && d.likelihood_rating == likelihood;
        });
        var count = cell_data ? cell_data.count : 0;
        var risk_class = self._get_risk_class(score);

        html += '<td class="risk-cell ' + risk_class + '" ';
        html += 'data-impact="' + impact + '" ';
        html += 'data-likelihood="' + likelihood + '" ';
        html += 'data-count="' + count + '">';
        html += count || "";
        html += "</td>";
      }

      html += "</tr>";
    }
    html += "</tbody></table>";

    $(container).html(html);

    // Add click handlers
    $(container)
      .find(".risk-cell")
      .on("click", function () {
        var impact = $(this).data("impact");
        var likelihood = $(this).data("likelihood");
        self._show_risks_at_level(impact, likelihood);
      });
  },

  /**
   * Get CSS class for risk score
   */
  _get_risk_class: function (score) {
    if (score >= 20) return "risk-critical";
    if (score >= 15) return "risk-high";
    if (score >= 10) return "risk-medium";
    if (score >= 5) return "risk-low";
    return "risk-very-low";
  },

  /**
   * Show risks at specific level
   */
  _show_risks_at_level: function (impact, likelihood) {
    frappe.set_route("List", "Risk Register Entry", {
      impact_rating: impact,
      likelihood_rating: likelihood,
      status: "Active",
    });
  },

  /**
   * Load compliance dashboard data
   * @param {function} callback - Callback with dashboard data
   */
  get_dashboard_data: function (callback) {
    frappe.call({
      method: "advanced_compliance.advanced_compliance.api.get_dashboard_data",
      callback: function (r) {
        if (r.message) {
          callback(r.message);
        }
      },
    });
  },

  /**
   * Show control details in dialog
   * @param {string} control_name - Control Activity name
   */
  show_control_details: function (control_name) {
    frappe.call({
      method: "advanced_compliance.advanced_compliance.api.get_control_details",
      args: { control_name: control_name },
      callback: function (r) {
        if (r.message) {
          var d = new frappe.ui.Dialog({
            title: r.message?.control_name || __("Control Details"),
            size: "large",
            fields: [
              {
                fieldtype: "HTML",
                fieldname: "control_html",
              },
            ],
          });

          d.fields_dict.control_html.$wrapper.html(
            advanced_compliance._render_control_details(r.message),
          );
          d.show();
        }
      },
    });
  },

  /**
   * Render control details HTML
   */
  _render_control_details: function (control) {
    var html = '<div class="control-details">';

    // Status badge
    html += '<div class="mb-3">';
    if (control?.status) {
      html +=
        '<span class="compliance-badge status-' +
        control.status.toLowerCase() +
        '">';
      html += control.status;
      html += "</span>";
    }
    if (control?.is_key_control) {
      html +=
        ' <span class="compliance-badge status-warning">Key Control</span>';
    }
    html += "</div>";

    // Details grid
    html += '<div class="row">';
    html += '<div class="col-md-6">';
    html +=
      "<p><strong>" +
      __("Owner") +
      ":</strong> " +
      (control.control_owner || "-") +
      "</p>";
    html +=
      "<p><strong>" +
      __("Type") +
      ":</strong> " +
      (control.control_type || "-") +
      "</p>";
    html +=
      "<p><strong>" +
      __("Frequency") +
      ":</strong> " +
      (control.frequency || "-") +
      "</p>";
    html += "</div>";
    html += '<div class="col-md-6">';
    html +=
      "<p><strong>" +
      __("Tests") +
      ":</strong> " +
      (control.test_count || 0) +
      "</p>";
    html +=
      "<p><strong>" +
      __("Open Deficiencies") +
      ":</strong> " +
      (control.open_deficiencies || 0) +
      "</p>";
    html +=
      "<p><strong>" +
      __("Last Test") +
      ":</strong> " +
      (control.last_test_date || __("Never")) +
      "</p>";
    html += "</div>";
    html += "</div>";

    // Description
    if (control.description) {
      html += '<div class="mt-3">';
      html += "<h6>" + __("Description") + "</h6>";
      html += "<p>" + control.description + "</p>";
      html += "</div>";
    }

    html += "</div>";
    return html;
  },

  /**
   * Export compliance data
   * @param {string} report_type - Type of report
   * @param {object} filters - Report filters
   */
  export_report: function (report_type, filters) {
    frappe.call({
      method: "advanced_compliance.advanced_compliance.api.export_report",
      args: {
        report_type: report_type,
        filters: filters,
      },
      callback: function (r) {
        if (r.message && r.message.file_url) {
          window.open(r.message.file_url);
        }
      },
    });
  },

  /**
   * Show help for a DocType
   * @param {string} doctype - DocType name
   * @param {string} field - Optional field name
   */
  show_help: function (doctype, field) {
    frappe.call({
      method: "advanced_compliance.advanced_compliance.help.get_help",
      args: {
        doctype: doctype,
        field: field,
      },
      callback: function (r) {
        if (r.message) {
          var d = new frappe.ui.Dialog({
            title: r.message.title || __("Help"),
            fields: [
              {
                fieldtype: "HTML",
                fieldname: "help_html",
              },
            ],
          });

          var html = '<div class="help-content">';
          html += "<p>" + (r.message.description || "") + "</p>";

          if (r.message.tips && r.message.tips.length) {
            html += "<h6>" + __("Tips") + "</h6><ul>";
            r.message.tips.forEach(function (tip) {
              html += "<li>" + tip + "</li>";
            });
            html += "</ul>";
          }

          html += "</div>";

          d.fields_dict.help_html.$wrapper.html(html);
          d.show();
        }
      },
    });
  },

  /**
   * Show Natural Language Query Dialog
   * Allows users to ask compliance questions in plain English
   */
  show_nl_query_dialog: function () {
    var self = this;

    var example_questions = [
      "Show me all high risk controls",
      "Which controls failed testing last month?",
      "What are the open deficiencies?",
      "How many tests were executed this quarter?",
      "List overdue controls",
      "Show me SOX controls",
    ];

    var d = new frappe.ui.Dialog({
      title: __("Ask Compliance Question"),
      size: "large",
      fields: [
        {
          fieldtype: "Data",
          fieldname: "question",
          label: __("Your Question"),
          placeholder: __("e.g., Show me all high risk controls"),
          reqd: 1,
        },
        {
          fieldtype: "Check",
          fieldname: "use_llm",
          label: __("Use AI for complex queries"),
          description: __(
            "Enable for questions the rule-based engine can't handle",
          ),
        },
        {
          fieldtype: "Section Break",
          label: __("Example Questions"),
        },
        {
          fieldtype: "HTML",
          fieldname: "examples_html",
        },
        {
          fieldtype: "Section Break",
          label: __("Results"),
        },
        {
          fieldtype: "HTML",
          fieldname: "results_html",
        },
      ],
      primary_action_label: __("Ask"),
      primary_action: function (values) {
        self._execute_nl_query(d, values.question, values.use_llm);
      },
    });

    // Render example questions as clickable chips
    var examples_html =
      '<div class="example-questions" style="margin-bottom: 15px;">';
    example_questions.forEach(function (q) {
      examples_html +=
        '<button class="btn btn-xs btn-default example-q" style="margin: 3px;" data-question="' +
        q +
        '">';
      examples_html += q;
      examples_html += "</button>";
    });
    examples_html += "</div>";
    d.fields_dict.examples_html.$wrapper.html(examples_html);

    // Click handler for example questions
    d.fields_dict.examples_html.$wrapper
      .find(".example-q")
      .on("click", function () {
        var question = $(this).data("question");
        d.set_value("question", question);
        self._execute_nl_query(d, question, d.get_value("use_llm"));
      });

    // Initial results placeholder
    d.fields_dict.results_html.$wrapper.html(
      '<div class="text-muted text-center" style="padding: 20px;">' +
        __("Ask a question to see results here") +
        "</div>",
    );

    d.show();

    // Focus on input
    setTimeout(function () {
      d.fields_dict.question.$input.focus();
    }, 300);
  },

  /**
   * Execute NL Query and display results
   */
  _execute_nl_query: function (dialog, question, use_llm) {
    var self = this;
    var results_wrapper = dialog.fields_dict.results_html.$wrapper;

    // Show loading
    results_wrapper.html(
      '<div class="text-center" style="padding: 20px;">' +
        '<i class="fa fa-spinner fa-spin fa-2x"></i>' +
        '<p class="text-muted">' +
        __("Searching...") +
        "</p>" +
        "</div>",
    );

    frappe.call({
      method:
        "advanced_compliance.advanced_compliance.intelligence.nlp.query_engine.ask_compliance_question",
      args: {
        question: question,
        use_llm: use_llm ? 1 : 0,
      },
      callback: function (r) {
        if (r.message) {
          self._render_nl_results(results_wrapper, r.message);
        }
      },
      error: function (r) {
        results_wrapper.html(
          '<div class="alert alert-danger">' +
            "<strong>" +
            __("Error") +
            ":</strong> " +
            (r.message || __("Failed to execute query")) +
            "</div>",
        );
      },
    });
  },

  /**
   * Render NL Query results
   */
  _render_nl_results: function (wrapper, result) {
    var html = "";

    if (!result.success) {
      html =
        '<div class="alert alert-warning">' +
        "<strong>" +
        __("Could not process query") +
        ":</strong> " +
        (result.error || __("Unknown error")) +
        "</div>";
      wrapper.html(html);
      return;
    }

    // Response summary
    html += '<div class="alert alert-info">';
    html += "<strong>" + result.response + "</strong>";
    if (result.query_type === "llm") {
      html += ' <span class="badge badge-primary">AI</span>';
    }
    html += "</div>";

    // Count query - just show the number
    if (result.query_type === "count") {
      html += '<div class="text-center" style="padding: 20px;">';
      html +=
        '<h1 style="font-size: 48px; color: var(--primary);">' +
        result.count +
        "</h1>";
      html += '<p class="text-muted">' + result.doctype + "</p>";
      html += "</div>";
      wrapper.html(html);
      return;
    }

    // List results
    if (result.results && result.results.length > 0) {
      html +=
        '<div class="frappe-list" style="max-height: 400px; overflow-y: auto;">';
      html += '<table class="table table-hover">';
      html += "<thead><tr>";

      // Get column headers from first result
      var columns = Object.keys(result.results[0])
        .filter(function (k) {
          return k !== "name" && !k.startsWith("_");
        })
        .slice(0, 5); // Limit to 5 columns
      columns.unshift("name");

      columns.forEach(function (col) {
        html += "<th>" + frappe.unscrub(col) + "</th>";
      });
      html += "</tr></thead>";
      html += "<tbody>";

      result.results.forEach(function (row) {
        html +=
          '<tr class="result-row" data-doctype="' +
          result.doctype +
          '" data-name="' +
          row.name +
          '" style="cursor: pointer;">';
        columns.forEach(function (col) {
          var value = row[col];
          if (value === null || value === undefined) {
            value = "-";
          } else if (typeof value === "boolean") {
            value = value ? "Yes" : "No";
          } else if (col === "name") {
            value =
              '<a href="/app/' +
              frappe.router.slug(result.doctype) +
              "/" +
              row.name +
              '">' +
              value +
              "</a>";
          }
          html += "<td>" + value + "</td>";
        });
        html += "</tr>";
      });

      html += "</tbody></table>";
      html += "</div>";

      // View all link
      if (result.count > result.results.length) {
        html += '<div class="text-center mt-3">';
        html +=
          '<a href="/app/' +
          frappe.router.slug(result.doctype) +
          '" class="btn btn-sm btn-default">';
        html += __("View All {0} Results", [result.count]);
        html += "</a>";
        html += "</div>";
      }
    } else {
      html += '<div class="text-center text-muted" style="padding: 20px;">';
      html += __("No results found");
      html += "</div>";
    }

    wrapper.html(html);

    // Click handler for rows
    wrapper.find(".result-row").on("click", function (e) {
      if (!$(e.target).is("a")) {
        var doctype = $(this).data("doctype");
        var name = $(this).data("name");
        frappe.set_route("Form", doctype, name);
      }
    });
  },
};

// Initialize on document ready
$(document).ready(function () {
  advanced_compliance.init();
});

// Add to Frappe namespace
frappe.advanced_compliance = advanced_compliance;
