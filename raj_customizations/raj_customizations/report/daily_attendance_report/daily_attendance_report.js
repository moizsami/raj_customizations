frappe.query_reports["Daily Attendance Report"] = {
  filters: [
    {
      fieldname: "from_date",
      label: "Date",
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.get_today(),
    },
  ],

  // Color full row red if first check-in > 09:00
  formatter: function (value, row, column, data, default_formatter) {
    const formatted = default_formatter(value, row, column, data);

    // Only when we have the full row (data) and a datetime present
    if (data && data.check_in_time) {
      try {
        // check_in_time comes as ISO-like string; moment is bundled in desk
        const t = moment(data.check_in_time);
        // Compare to 09:00 of the same day (local time in browser)
        const threshold = moment(t).hour(9).minute(0).second(0);

        // mark the entire row if late
        if (t.isAfter(threshold)) {
          // Find the datatable row and decorate once
          const $row = $(
            `.dt-row[data-row-index="${row}"], .dt-row-odd[data-row-index="${row}"], .dt-row-even[data-row-index="${row}"]`
          );
          if ($row && !$row.hasClass("late-row")) {
            $row.addClass("late-row");
          }
        }
      } catch (e) {
        // ignore formatting errors silently
      }
    }
    return formatted;
  },

  onload: function (report) {
    // Inject a simple CSS for "late" rows (soft red bg + darker red text)
    const styleId = "daily-checkins-late-style";
    if (!document.getElementById(styleId)) {
      const style = document.createElement("style");
      style.id = styleId;
      style.textContent = `
        .late-row .dt-cell__content { color: #9b1c1c !important; }
        .late-row { background: #ffe5e5 !important; }
      `;
      document.head.appendChild(style);
    }
  },
};
