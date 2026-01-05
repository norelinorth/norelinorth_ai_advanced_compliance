// Copyright (c) 2024, Norlei North and contributors
// For license information, please see license.txt

frappe.ui.form.on("Control Activity", {
  refresh(frm) {
    // Add status indicator
    frm.set_indicator_formatter("status", function (doc) {
      const status_colors = {
        Draft: "orange",
        Active: "green",
        "Under Review": "yellow",
        Deprecated: "red",
      };
      return status_colors[doc.status] || "grey";
    });

    // Show test result indicator
    if (frm.doc.last_test_result) {
      const result_colors = {
        Effective: "green",
        "Ineffective - Minor": "yellow",
        "Ineffective - Significant": "orange",
        "Ineffective - Material": "red",
        "Not Tested": "grey",
      };
      frm.dashboard.set_headline_alert(
        `<span class="indicator ${
          result_colors[frm.doc.last_test_result] || "grey"
        }">
                    ${__("Last Test Result")}: ${frm.doc.last_test_result}
                </span>`,
      );
    }

    // Add button to create test execution
    if (frm.doc.status === "Active" && !frm.is_new()) {
      frm.add_custom_button(
        __("Create Test Execution"),
        function () {
          frappe.new_doc("Test Execution", {
            control: frm.doc.name,
            control_name: frm.doc.control_name,
            tester: frappe.session.user,
          });
        },
        __("Actions"),
      );
    }

    // Add button to view related risks
    if (
      !frm.is_new() &&
      frm.doc.risks_addressed &&
      frm.doc.risks_addressed.length > 0
    ) {
      frm.add_custom_button(
        __("View Linked Risks"),
        function () {
          const risk_names = frm.doc.risks_addressed.map((r) => r.risk);
          frappe.set_route("List", "Risk Register Entry", {
            name: ["in", risk_names],
          });
        },
        __("View"),
      );
    }

    // Show overdue test warning
    if (
      frm.doc.next_test_date &&
      frappe.datetime.get_diff(
        frm.doc.next_test_date,
        frappe.datetime.nowdate(),
      ) < 0
    ) {
      frm.dashboard.set_headline_alert(
        `<span class="indicator red">
                    ${__("Test Overdue!")} ${__("Due date was")} ${
                      frm.doc.next_test_date
                    }
                </span>`,
        "red",
      );
    }
  },

  coso_component(frm) {
    // Filter COSO Principle based on selected component
    if (frm.doc.coso_component) {
      frm.set_query("coso_principle", function () {
        return {
          filters: {
            component: frm.doc.coso_component,
          },
        };
      });
    } else {
      frm.set_query("coso_principle", function () {
        return {};
      });
    }
    // Clear principle if component changes
    if (frm.doc.coso_principle) {
      frm.set_value("coso_principle", "");
    }
  },

  is_key_control(frm) {
    // Warn and require test frequency for key controls
    if (frm.doc.is_key_control && !frm.doc.test_frequency) {
      frappe.msgprint({
        title: __("Key Control Requirements"),
        indicator: "orange",
        message: __("Key Controls require a Test Frequency. Please set one."),
      });
    }
  },

  control_category(frm) {
    // Suggest control type based on category
    if (frm.doc.control_category === "IT General Controls") {
      if (!frm.doc.automation_level) {
        frm.set_value("automation_level", "Semi-automated");
      }
    }
  },
});
