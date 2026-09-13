// Copyright (c) 2026, moiz@samtech-solutions.com and contributors
// For license information, please see license.txt

frappe.query_reports["Stock List Report"] = {
  filters: [
    {
      fieldname: "item_group",
      label: "Item Group",
      fieldtype: "Link",
      options: "Item Group",
    },
    {
      fieldname: "warehouse",
      label: "Warehouse",
      fieldtype: "Link",
      options: "Warehouse",
    },
    {
      fieldname: "price_list",
      label: "Price List",
      fieldtype: "Link",
      options: "Price List",
      reqd: 1,
      default: frappe.defaults.get_user_default("selling_price_list"),
    },
  ],
};
