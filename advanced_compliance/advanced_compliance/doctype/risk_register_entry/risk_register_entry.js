// Copyright (c) 2024, Norlei North and contributors
// For license information, please see license.txt

// Frappe v16 compatible - no global variables
frappe.ui.form.on("Risk Register Entry", {
  refresh(frm) {
    // Add status indicator
    frm.set_indicator_formatter("status", function (doc) {
      const status_colors = {
        Open: "red",
        Mitigated: "green",
        Accepted: "blue",
        Transferred: "purple",
        Closed: "grey",
      };
      return status_colors[doc.status] || "grey";
    });

    // Show risk level indicator
    if (frm.doc.residual_risk_score) {
      const risk_level = _get_risk_level(frm.doc.residual_risk_score);
      const level_colors = {
        Critical: "red",
        High: "orange",
        Medium: "yellow",
        Low: "green",
      };
      frm.dashboard.set_headline_alert(
        `<span class="indicator ${level_colors[risk_level] || "grey"}">
                    ${__("Risk Level")}: ${risk_level} (${__("Score")}: ${
                      frm.doc.residual_risk_score
                    })
                </span>`,
      );
    }

    // Add button to link control
    if (!frm.is_new()) {
      frm.add_custom_button(
        __("Link Control"),
        function () {
          frappe.prompt(
            {
              fieldtype: "Link",
              options: "Control Activity",
              label: __("Control Activity"),
              fieldname: "control",
              reqd: 1,
              get_query: function () {
                return {
                  filters: { status: "Active" },
                };
              },
            },
            function (values) {
              let row = frm.add_child("mitigating_controls");
              row.control = values.control;
              frm.refresh_field("mitigating_controls");
              frm.save();
            },
            __("Link Mitigating Control"),
            __("Add"),
          );
        },
        __("Actions"),
      );
    }

    // Show heat map visualization
    if (frm.doc.inherent_risk_score && frm.doc.residual_risk_score) {
      const reduction =
        frm.doc.inherent_risk_score - frm.doc.residual_risk_score;
      if (reduction > 0) {
        frm.dashboard.add_comment(
          __("Risk reduced by {0} points through controls", [reduction]),
          "green",
          true,
        );
      }
    }
  },

  inherent_likelihood(frm) {
    _calculate_inherent_score(frm);
  },

  inherent_impact(frm) {
    _calculate_inherent_score(frm);
  },

  residual_likelihood(frm) {
    _calculate_residual_score(frm);
  },

  residual_impact(frm) {
    _calculate_residual_score(frm);
  },
});

// Private helper functions (Frappe v16 compatible - defined within module scope)
const _calculate_inherent_score = function (frm) {
  if (frm.doc.inherent_likelihood && frm.doc.inherent_impact) {
    const likelihood =
      parseInt(frm.doc.inherent_likelihood.split(" - ")[0]) || 0;
    const impact = parseInt(frm.doc.inherent_impact.split(" - ")[0]) || 0;
    frm.set_value("inherent_risk_score", likelihood * impact);
  }
};

const _calculate_residual_score = function (frm) {
  if (frm.doc.residual_likelihood && frm.doc.residual_impact) {
    const likelihood =
      parseInt(frm.doc.residual_likelihood.split(" - ")[0]) || 0;
    const impact = parseInt(frm.doc.residual_impact.split(" - ")[0]) || 0;
    const score = likelihood * impact;
    frm.set_value("residual_risk_score", score);

    // Update risk level display
    const risk_level = _get_risk_level(score);
    frappe.show_alert(
      {
        message: __("Risk Level: {0}", [risk_level]),
        indicator: _get_risk_color(risk_level),
      },
      3,
    );
  }
};

const _get_risk_level = function (score) {
  // Default thresholds - should match Compliance Settings
  if (score >= 16) return "Critical";
  if (score >= 12) return "High";
  if (score >= 5) return "Medium";
  return "Low";
};

const _get_risk_color = function (level) {
  const colors = {
    Critical: "red",
    High: "orange",
    Medium: "yellow",
    Low: "green",
  };
  return colors[level] || "grey";
};
