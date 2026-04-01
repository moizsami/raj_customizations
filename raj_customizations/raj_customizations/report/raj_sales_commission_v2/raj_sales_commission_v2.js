// Copyright (c) 2026, moiz@samtech-solutions.com and contributors
// For license information, please see license.txt

frappe.query_reports["Raj Sales Commission V2"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: erpnext.utils.get_fiscal_year(
        frappe.datetime.get_today(),
        true,
      )[1],
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      //default: frappe.datetime.get_last_day(frappe.datetime.get_today()),
      default: erpnext.utils.get_fiscal_year(
        frappe.datetime.get_today(),
        true,
      )[2],
      reqd: 1,
    },

    // {
    // 	fieldname: "customer_group",
    // 	label: __("Sales Person"),
    // 	fieldtype: "Link",
    // 	//default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
    // 	options:"Customer Group",
    // 	reqd: 1,
    // },
    {
      fieldname: "customer_group",
      label: __("Sales Person"),
      fieldtype: "Link",
      options: "Sales Person",
      reqd: 0,
      get_query: () => {
        const company = frappe.query_report.get_filter_value("company");
        return {
          filters: {
            // Add your conditions here
            //company: company, // Example: Filter by company
            custom_commission_rule: ["!=", ""], // Example: Only show non-group cost centers
          },
        };
      },
    },
  ],
};
