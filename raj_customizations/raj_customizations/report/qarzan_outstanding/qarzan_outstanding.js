// Copyright (c) 2026, Samtech and contributors
// For license information, please see license.txt

frappe.query_reports["Qarzan Outstanding"] = {
	filters: [
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
			default: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][
				new Date().getMonth()
			],
			reqd: 1,
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Select",
			options: (() => {
				const y = new Date().getFullYear();
				const out = [];
				for (let i = y + 1; i >= 2020; i--) out.push(String(i));
				return out;
			})(),
			default: String(new Date().getFullYear()),
			reqd: 1,
		},
	],
};
