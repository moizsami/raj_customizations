frappe.ui.form.on("Journal Entry Account", {
	account: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (!row.account) return;

		frappe.db.get_value("Account", row.account, "root_type").then(({ message }) => {
			let is_expense = message && message.root_type === "Expense";
			let grid_row = frm.fields_dict.accounts.grid.grid_rows_by_docname[cdn];

			if (is_expense) {
				frappe.model.set_value(cdt, cdn, "cost_center", "");
			}

			if (grid_row) {
				grid_row.toggle_reqd("cost_center", is_expense);
			}
		});
	},
});
