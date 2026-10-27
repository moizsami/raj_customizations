import frappe
from frappe import _


def validate_cost_center_for_expense_accounts(doc, method=None):
	"""Cost Center is mandatory on every Journal Entry row whose account
	belongs to the Expense root type."""
	root_type_cache = {}

	for row in doc.accounts:
		if not row.account:
			continue

		root_type = root_type_cache.get(row.account)
		if root_type is None:
			root_type = frappe.db.get_value("Account", row.account, "root_type")
			root_type_cache[row.account] = root_type

		if root_type == "Expense" and not row.cost_center:
			frappe.throw(
				_("Row #{0}: Cost Center is mandatory for Expense Account {1}").format(
					row.idx, frappe.bold(row.account)
				)
			)
