frappe.pages["ask-compliance"].on_page_load = function (wrapper) {
  var page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Ask Compliance Question"),
    single_column: true,
  });

  new AskCompliance(page);
};

class AskCompliance {
  constructor(page) {
    this.page = page;
    this.ai_enabled = false;
    this.setup_page();
    this.check_ai_status();
  }

  async check_ai_status() {
    var self = this;
    // Check if AI is enabled in settings
    try {
      const response = await frappe.call({
        method: "frappe.client.get_value",
        args: {
          doctype: "AI Provider Settings",
          fieldname: "enable_nl_queries",
        },
      });

      if (response.message && response.message.enable_nl_queries) {
        self.ai_enabled = true;
        $(self.page.main)
          .find(".ai-status")
          .html(
            `<span class="text-success"><i class="fa fa-check-circle"></i> ${__(
              "AI Enhanced",
            )}</span>`,
          );
      } else {
        $(self.page.main)
          .find(".ai-status")
          .html(
            `<span class="text-muted"><i class="fa fa-info-circle"></i> ${__(
              "Rule-based mode",
            )}</span>`,
          );
      }
    } catch (error) {
      // If check fails, default to rule-based mode
      $(self.page.main)
        .find(".ai-status")
        .html(
          `<span class="text-muted"><i class="fa fa-info-circle"></i> ${__(
            "Rule-based mode",
          )}</span>`,
        );
    }
  }

  setup_page() {
    var self = this;

    // Example questions
    var examples = [
      __("Show me all high risk controls"),
      __("Which controls failed testing last month?"),
      __("What are the open deficiencies?"),
      __("How many tests were executed this quarter?"),
      __("List overdue controls"),
      __("Show me SOX controls"),
      __("Show me all risks"),
      __("List manual controls"),
      __("Show me critical deficiencies"),
    ];

    // Build page content
    var html = `
			<div class="ask-compliance-container" style="max-width: 900px; margin: 0 auto; padding: 20px;">
				<div class="search-section mb-4">
					<div class="input-group input-group-lg">
						<input type="text" class="form-control question-input"
							placeholder="${__("Ask a question about your compliance data...")}"
							style="font-size: 16px;">
						<div class="input-group-append">
							<button class="btn btn-primary ask-btn" type="button">
								<i class="fa fa-search"></i> ${__("Ask")}
							</button>
						</div>
					</div>
					<div class="mt-2 ai-status">
						<span class="text-muted"><i class="fa fa-spinner fa-spin"></i> ${__(
              "Checking AI status...",
            )}</span>
					</div>
				</div>

				<div class="examples-section mb-4">
					<h6 class="text-muted">${__("Try these examples:")}</h6>
					<div class="example-buttons">
						${examples
              .map(
                (q) => `
							<button class="btn btn-sm btn-outline-secondary example-btn mb-2 mr-2" data-question="${q}">
								${q}
							</button>
						`,
              )
              .join("")}
					</div>
				</div>

				<div class="results-section">
					<div class="results-placeholder text-center text-muted p-5">
						<i class="fa fa-comments fa-3x mb-3" style="opacity: 0.3;"></i>
						<p>${__("Ask a question to see results")}</p>
					</div>
					<div class="results-content" style="display: none;"></div>
				</div>
			</div>
		`;

    $(this.page.main).html(html);

    // Event handlers
    $(this.page.main)
      .find(".ask-btn")
      .on("click", function () {
        self.ask_question();
      });

    $(this.page.main)
      .find(".question-input")
      .on("keypress", function (e) {
        if (e.which === 13) {
          self.ask_question();
        }
      });

    $(this.page.main)
      .find(".example-btn")
      .on("click", function () {
        var question = $(this).data("question");
        $(self.page.main).find(".question-input").val(question);
        self.ask_question();
      });

    // Focus on input
    setTimeout(function () {
      $(self.page.main).find(".question-input").focus();
    }, 300);
  }

  ask_question() {
    var self = this;
    var question = $(this.page.main).find(".question-input").val().trim();

    if (!question) {
      frappe.show_alert({
        message: __("Please enter a question"),
        indicator: "orange",
      });
      return;
    }

    // Show loading
    $(this.page.main).find(".results-placeholder").hide();
    $(this.page.main)
      .find(".results-content")
      .html(
        `
			<div class="text-center p-5">
				<i class="fa fa-spinner fa-spin fa-2x"></i>
				<p class="text-muted mt-2">${__("Searching...")}</p>
			</div>
		`,
      )
      .show();

    // Always run rule-based query first
    frappe.call({
      method:
        "advanced_compliance.advanced_compliance.intelligence.nlp.query_engine.ask_compliance_question",
      args: {
        question: question,
        use_llm: 0,
      },
      callback: function (r) {
        if (r.message) {
          var rule_result = r.message;

          // If AI is enabled and rule-based didn't find good results, also try AI
          if (
            self.ai_enabled &&
            (!rule_result.success || rule_result.count === 0)
          ) {
            self.run_ai_query(question, rule_result);
          } else if (self.ai_enabled) {
            // AI enabled and rule-based found results - show both
            self.run_ai_query(question, rule_result);
          } else {
            // AI not enabled - just show rule-based results
            self.render_results(rule_result, null);
          }
        }
      },
      error: function (r) {
        $(self.page.main).find(".results-content").html(`
					<div class="alert alert-danger">
						<strong>${__("Error")}:</strong> ${r.message || __("Failed to execute query")}
					</div>
				`);
      },
    });
  }

  run_ai_query(question, rule_result) {
    var self = this;

    frappe.call({
      method:
        "advanced_compliance.advanced_compliance.intelligence.nlp.query_engine.ask_compliance_question",
      args: {
        question: question,
        use_llm: 1,
      },
      callback: function (r) {
        self.render_results(rule_result, r.message);
      },
      error: function (err) {
        // AI query failed, just show rule-based
        self.render_results(rule_result, null);
      },
    });
  }

  render_results(rule_result, ai_result) {
    var html = "";

    // Determine which result to show prominently
    var primary_result = rule_result;
    var secondary_result = ai_result;

    // If AI result has more results or rule-based failed, swap them
    if (ai_result && ai_result.success) {
      if (
        !rule_result.success ||
        ai_result.count > rule_result.count ||
        (rule_result.count === 0 && ai_result.count > 0)
      ) {
        primary_result = ai_result;
        secondary_result = rule_result;
      }
    }

    // Show primary result
    html += this.render_single_result(primary_result, true);

    // Show secondary result if different and has results
    if (
      secondary_result &&
      secondary_result.success &&
      secondary_result !== primary_result
    ) {
      var has_different_results =
        secondary_result.count !== primary_result.count ||
        secondary_result.doctype !== primary_result.doctype;

      if (has_different_results) {
        html += `<hr class="my-4">`;
        html += `<h6 class="text-muted mb-3">
					${
            secondary_result.query_type === "llm"
              ? '<i class="fa fa-robot"></i> ' + __("AI Interpretation")
              : '<i class="fa fa-cogs"></i> ' + __("Pattern Match")
          }
				</h6>`;
        html += this.render_single_result(secondary_result, false);
      }
    }

    $(this.page.main).find(".results-content").html(html);
  }

  render_single_result(result, is_primary) {
    var html = "";

    if (!result || !result.success) {
      if (is_primary) {
        html = `
					<div class="alert alert-warning">
						<strong>${__("Could not process query")}:</strong>
						${result ? result.error || __("Unknown error") : __("No response")}
					</div>
				`;
      }
      return html;
    }

    // Response summary (escape to prevent XSS)
    var safe_response = frappe.utils.xss_sanitise(result.response || "");
    var safe_doctype = frappe.utils.xss_sanitise(result.doctype || "");

    var badge = "";
    if (result.query_type === "llm") {
      badge =
        ' <span class="badge badge-primary"><i class="fa fa-robot"></i> AI</span>';
    } else {
      badge =
        ' <span class="badge badge-secondary"><i class="fa fa-cogs"></i> Pattern</span>';
    }

    html += `
			<div class="alert ${is_primary ? "alert-info" : "alert-light"}">
				<strong>${safe_response}</strong>${badge}
			</div>
		`;

    // Count query
    if (result.query_type === "count") {
      html += `
				<div class="text-center p-5">
					<h1 style="font-size: 72px; color: var(--primary);">${cint(result.count)}</h1>
					<p class="text-muted h5">${safe_doctype}</p>
				</div>
			`;
      return html;
    }

    // List results
    if (result.results && result.results.length > 0) {
      html += `<div class="table-responsive" style="max-height: 400px; overflow-y: auto;">`;
      html += `<table class="table table-hover table-sm">`;
      html += `<thead class="bg-light"><tr>`;

      // Get columns
      var columns = Object.keys(result.results[0])
        .filter(function (k) {
          return k !== "name" && !k.startsWith("_");
        })
        .slice(0, 5);
      columns.unshift("name");

      columns.forEach(function (col) {
        html += `<th>${frappe.unscrub(col)}</th>`;
      });
      html += `</tr></thead><tbody>`;

      var doctype_slug = frappe.router.slug(result.doctype);

      result.results.forEach(function (row) {
        var safe_name = frappe.utils.xss_sanitise(row.name || "");
        html += `<tr style="cursor: pointer;" onclick="frappe.set_route('Form', '${safe_doctype}', '${safe_name}')">`;
        columns.forEach(function (col) {
          var value = row[col];
          if (value === null || value === undefined) {
            value = "-";
          } else if (typeof value === "boolean") {
            value = value ? __("Yes") : __("No");
          } else if (col === "name") {
            value = `<a href="/app/${doctype_slug}/${safe_name}">${safe_name}</a>`;
          } else {
            value = frappe.utils.xss_sanitise(String(value));
          }
          html += `<td>${value}</td>`;
        });
        html += `</tr>`;
      });

      html += `</tbody></table></div>`;

      // View all link
      if (result.count > result.results.length) {
        html += `
					<div class="text-center mt-3">
						<a href="/app/${doctype_slug}" class="btn btn-sm btn-default">
							${__("View All {0} Results", [result.count])}
						</a>
					</div>
				`;
      }
    } else if (is_primary) {
      html += `
				<div class="text-center text-muted p-5">
					<i class="fa fa-search fa-2x mb-3" style="opacity: 0.3;"></i>
					<p>${__("No results found")}</p>
				</div>
			`;
    }

    return html;
  }
}
