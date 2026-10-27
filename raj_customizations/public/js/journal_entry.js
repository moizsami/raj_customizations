frappe.ui.form.on("Journal Entry Account", {
  account: function (frm, cdt, cdn) {
    let row = locals[cdt] && locals[cdt][cdn];

    if (!row || !row.account) return;

    frappe.db
      .get_value("Account", row.account, "root_type")
      .then(({ message }) => {
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

const CC_ALLOCATION = "Cost Center Expense Allocation";
const CC_AMOUNT_FIELDS = [
  "debit_in_account_currency",
  "credit_in_account_currency",
];

frappe.ui.form.on("Journal Entry", {
  async before_save(frm) {
    // only split rows when saving a draft
    if (frm.doc.docstatus !== 0) return;

    const new_rows = [];
    let changed = false;

    for (const row of frm.doc.accounts || []) {
      const children = await get_allocation_children(frm, row);

      if (!children.length) {
        new_rows.push(copy_row(row));
        continue;
      }

      changed = true;
      const used = {
        debit_in_account_currency: 0,
        credit_in_account_currency: 0,
      };

      // child rows are pushed right after each other, so they stay in order
      children.forEach((child, i) => {
        const is_last = i === children.length - 1;
        const new_row = copy_row(row);
        new_row.cost_center = child.cost_center;

        CC_AMOUNT_FIELDS.forEach((field) => {
          const decimals = precision(field, row);
          // last row takes the rounding remainder so the total stays exact
          new_row[field] = is_last
            ? flt(row[field] - used[field], decimals)
            : flt((row[field] * child.percentage) / 100, decimals);
          used[field] += new_row[field];
        });

        new_rows.push(new_row);
      });
    }

    if (!changed) return;

    frm.clear_table("accounts");
    new_rows.forEach((values) => frm.add_child("accounts", values));
    frm.refresh_field("accounts");
  },
});

// child rows of the latest submitted allocation matching this row, or []
async function get_allocation_children(frm, row) {
  if (!row.account || !row.cost_center) return [];

  const matches = await frappe.db.get_list(CC_ALLOCATION, {
    filters: {
      docstatus: 1,
      company: frm.doc.company,
      expense_account: row.account,
      main_cost_center: row.cost_center,
      valid_from: ["<=", frm.doc.posting_date],
    },
    fields: ["name"],
    order_by: "valid_from desc, creation desc",
    limit: 1,
  });
  if (!matches.length) return [];

  const allocation = await frappe.db.get_doc(CC_ALLOCATION, matches[0].name);
  return allocation.allocation_percentages || [];
}

// plain copy of a row's values, without the keys that identify the row itself
function copy_row(row) {
  const { name, idx, parent, parenttype, parentfield, doctype, ...values } =
    row;
  return values;
}
