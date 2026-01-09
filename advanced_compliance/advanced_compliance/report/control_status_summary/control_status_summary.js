// Copyright (c) 2024, Norlei North and contributors
// For license information, please see license.txt

frappe.query_reports["Control Status Summary"] = {
  filters: [
    {
      fieldname: "status",
      label: __("Status"),
      fieldtype: "Select",
      options: "\nDraft\nActive\nUnder Review\nDeprecated",
    },
    {
      fieldname: "control_type",
      label: __("Control Type"),
      fieldtype: "Select",
      options: "\nPreventive\nDetective\nCorrective",
    },
    {
      fieldname: "is_key_control",
      label: __("Key Controls Only"),
      fieldtype: "Check",
    },
    {
      fieldname: "control_owner",
      label: __("Control Owner"),
      fieldtype: "Link",
      options: "User",
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (column.fieldname === "test_status" && data?.test_status) {
      if (data.test_status === "Overdue") {
        value = `<span class="indicator-pill red">${value}</span>`;
      } else if (data.test_status === "Due Soon") {
        value = `<span class="indicator-pill orange">${value}</span>`;
      } else if (data.test_status === "On Track") {
        value = `<span class="indicator-pill green">${value}</span>`;
      }
    }

    if (column.fieldname === "last_test_result") {
      if (
        value &&
        value.includes("Effective") &&
        !value.includes("Ineffective")
      ) {
        value = `<span class="indicator-pill green">${value}</span>`;
      } else if (value && value.includes("Ineffective")) {
        if (value.includes("Material")) {
          value = `<span class="indicator-pill red">${value}</span>`;
        } else if (value.includes("Significant")) {
          value = `<span class="indicator-pill orange">${value}</span>`;
        } else {
          value = `<span class="indicator-pill yellow">${value}</span>`;
        }
      }
    }

    if (column.fieldname === "status" && data?.status) {
      const colors = {
        Draft: "orange",
        Active: "green",
        "Under Review": "yellow",
        Deprecated: "red",
      };
      const color = colors[data.status] || "grey";
      value = `<span class="indicator-pill ${color}">${value}</span>`;
    }

    return value;
  },
};
