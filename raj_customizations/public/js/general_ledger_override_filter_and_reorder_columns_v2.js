frappe.router.on("change", function () {
  let route = frappe.get_route();

  if (route[0] === "query-report" && route[1] === "General Ledger") {
    let attempts = 0;
    let interval = setInterval(function () {
      attempts++;

      if (
        frappe.query_report &&
        frappe.query_report.report_name === "General Ledger" &&
        frappe.query_report.get_filter("show_remarks")
      ) {
        frappe.query_report.get_filter("show_remarks").set_value(1);
        console.log("✅ show_remarks set");

        let observer = new MutationObserver(function () {
          reorder_remarks_column();
        });

        observer.observe(
          document.querySelector(".dt-scrollable") || document.body,
          {
            childList: true,
            subtree: true,
          },
        );

        console.log("✅ MutationObserver attached");
        clearInterval(interval);
      }

      if (attempts > 50) clearInterval(interval);
    }, 100);
  }
});

function reorder_remarks_column() {
  let columns = frappe.query_report && frappe.query_report.columns;
  if (!columns || !columns.length) return;

  console.log("frappe.query_report.columns22222");
  console.log(frappe.query_report.columns);
  console.log("frappe.query_report.columns11111");
  // Remove "GL Entry" column
  let gl_idx = columns.findIndex((c) => c.fieldname === "gl_entry");

  if (gl_idx !== -1) {
    columns.splice(gl_idx, 1);
    console.log("✅ GL Entry column removed");
  }

  let remarks_idx = columns.findIndex((c) => c.fieldname === "remarks");
  let balance_idx = columns.findIndex((c) => c.fieldname === "balance");

  if (remarks_idx === -1 || balance_idx === -1) return;

  // Already in correct position — do nothing
  if (remarks_idx === balance_idx + 1) return;

  let remarks_col = columns.splice(remarks_idx, 1)[0];
  balance_idx = columns.findIndex((c) => c.fieldname === "balance");
  columns.splice(balance_idx + 1, 0, remarks_col);

  console.log("✅ Remarks moved after Balance");

  // Find the correct function name for refreshing
  let qr = frappe.query_report;
  try {
    if (typeof qr.datatable.refresh === "function") {
      // Build data the correct way
      let data = qr.data || qr.report_data || [];
      qr.datatable.refresh(data, columns);
      console.log("✅ refreshed via datatable.refresh");
    }
  } catch (e) {
    console.log("datatable.refresh failed:", e);
    try {
      qr.render_report();
      console.log("✅ refreshed via render_report");
    } catch (e2) {
      console.log("render_report failed:", e2);
      try {
        qr.setup_report();
        console.log("✅ refreshed via setup_report");
      } catch (e3) {
        console.log("❌ all refresh methods failed:", e3);
        // Log available methods to find the right one
        console.log(
          "Available methods:",
          Object.getOwnPropertyNames(Object.getPrototypeOf(qr)),
        );
      }
    }
  }
}
