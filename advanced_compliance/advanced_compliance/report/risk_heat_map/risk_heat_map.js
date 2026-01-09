// Copyright (c) 2024, Norlei North and contributors
// For license information, please see license.txt

frappe.query_reports["Risk Heat Map"] = {
  filters: [
    {
      fieldname: "status",
      label: __("Status"),
      fieldtype: "Select",
      options: "\nOpen\nMitigated\nAccepted\nTransferred\nClosed",
    },
    {
      fieldname: "risk_category",
      label: __("Category"),
      fieldtype: "Link",
      options: "Risk Category",
    },
    {
      fieldname: "risk_owner",
      label: __("Risk Owner"),
      fieldtype: "Link",
      options: "User",
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (column.fieldname === "risk_level" && data?.risk_level) {
      const colors = {
        Critical: "red",
        High: "orange",
        Medium: "yellow",
        Low: "green",
      };
      const color = colors[data.risk_level] || "grey";
      value = `<span class="indicator-pill ${color}">${value}</span>`;
    }

    if (column.fieldname === "status" && data?.status) {
      const colors = {
        Open: "red",
        Mitigated: "green",
        Accepted: "blue",
        Transferred: "purple",
        Closed: "grey",
      };
      const color = colors[data.status] || "grey";
      value = `<span class="indicator-pill ${color}">${value}</span>`;
    }

    if (
      column.fieldname === "residual_risk_score" &&
      data?.residual_risk_score != null
    ) {
      let color = "green";
      if (data.residual_risk_score >= 16) color = "red";
      else if (data.residual_risk_score >= 12) color = "orange";
      else if (data.residual_risk_score >= 5) color = "yellow";

      value = `<span class="indicator-pill ${color}">${value}</span>`;
    }

    return value;
  },
};
