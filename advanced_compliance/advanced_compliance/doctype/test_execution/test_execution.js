// Copyright (c) 2024, Norlei North and contributors
// For license information, please see license.txt

frappe.ui.form.on("Test Execution", {
  refresh(frm) {
    // No custom buttons needed - upload is handled in the child table row
  },
});

// Handle the child table
frappe.ui.form.on("Test Evidence", {
  form_render(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let grid_row = frm.fields_dict.evidence.grid.grid_rows_by_docname[cdn];

    // The form_area is on grid_form, not directly on grid_row
    if (grid_row && grid_row.grid_form) {
      let $wrapper = grid_row.grid_form.form_area;

      // Hide the standard Attach field - we use our custom uploader instead
      $wrapper.find('[data-fieldname="attachment"]').hide();

      // Remove any existing custom upload button
      $wrapper.find(".custom-upload-btn").remove();

      // Add a prominent upload button with NATIVE file input
      let $upload_container = $(`
                <div class="custom-upload-btn" style="margin: 15px 0; padding: 15px; background: #e3f2fd; border: 2px solid #1976d2; border-radius: 8px;">
                    <label class="btn btn-primary" style="cursor: pointer; margin: 0;">
                        <i class="fa fa-upload"></i> ${__(
                          "Click to Upload File",
                        )}
                        <input type="file" style="display: none;" class="evidence-file-input">
                    </label>
                    <span class="file-status" style="margin-left: 15px; color: #1565c0; font-weight: 500;">
                        ${
                          row.attachment
                            ? __("Current: ") + row.attachment
                            : __("No file attached yet")
                        }
                    </span>
                </div>
            `);

      // Handle file selection with native input
      $upload_container.find(".evidence-file-input").on("change", function (e) {
        let file = e.target.files[0];
        if (file) {
          _upload_file_for_row(frm, cdt, cdn, file, $upload_container);
        }
      });

      // Insert at the beginning of the form
      $wrapper.prepend($upload_container);
    }
  },

  evidence_add(frm, cdt, cdn) {
    // When a new row is added, set default evidence type
    frappe.model.set_value(cdt, cdn, "evidence_type", "Screenshot");

    // Expand the row to show the upload button
    setTimeout(() => {
      let grid = frm.fields_dict.evidence.grid;
      let grid_row = grid.grid_rows_by_docname[cdn];
      if (grid_row) {
        grid_row.toggle_view(true);
      }
    }, 100);
  },
});

// Private helper function (Frappe v16 compatible - defined within module scope)
const _upload_file_for_row = function (frm, cdt, cdn, file, $container) {
  $container.find(".file-status").text(__("Uploading..."));

  let formData = new FormData();
  formData.append("file", file);
  formData.append("doctype", frm.doctype);
  formData.append("docname", frm.docname);
  formData.append("folder", "Home/Attachments");
  formData.append("is_private", 1);

  $.ajax({
    url: "/api/method/upload_file",
    type: "POST",
    data: formData,
    processData: false,
    contentType: false,
    headers: {
      "X-Frappe-CSRF-Token": frappe.csrf_token,
    },
    success: function (response) {
      let file_url = response.message.file_url;

      // Update the row
      frappe.model.set_value(cdt, cdn, "attachment", file_url);
      let row = locals[cdt][cdn];
      if (!row.description) {
        frappe.model.set_value(cdt, cdn, "description", file.name);
      }

      frm.refresh_field("evidence");
      $container.find(".file-status").text(__("Uploaded: ") + file.name);

      frappe.show_alert({
        message: __("File uploaded: {0}", [file.name]),
        indicator: "green",
      });
    },
    error: function (xhr, status, error) {
      $container.find(".file-status").text(__("Upload failed!"));
      frappe.msgprint({
        title: __("Upload Error"),
        indicator: "red",
        message: __("Failed to upload file: {0}", [error]),
      });
    },
  });
};
