# paper_stock_monthly_analysis.py

import frappe
from frappe import _
from frappe.utils import getdate, add_months, add_days
from frappe.utils.nestedset import get_descendants_of


def execute(filters=None):
	if not filters:
		filters = {}

	validate_filters(filters)

	fiscal_year = filters["fiscal_year"]
	item_group = filters.get("item_group")
	company = filters.get("company")

	months = get_fiscal_months(fiscal_year)
	warehouses = get_valid_warehouses()
	items = get_items_under_group(item_group)

	columns = get_columns(months)
	data = []

	for wh in warehouses:
		row = {
			"warehouse": wh.name,
			"warehouse_name": wh.warehouse_name,
		}
		for label, date in months:
			opening_qty = 0
			for item in items:
				qty = get_latest_qty_snapshot(item.name, wh.name, date)
				opening_qty += qty
				# Optional debug for Jan
				# if label == "Jan 2025":
				#     frappe.log_error(f"DEBUG: {item.name} @ {wh.name} on {date} → {qty}", "Opening Debug")
			row[label] = opening_qty
		data.append(row)

	return columns, data


def validate_filters(filters):
	if not filters.get("fiscal_year"):
		frappe.throw(_("Fiscal Year is required"))
	if not filters.get("item_group"):
		frappe.throw(_("Item Group is required"))
	if not filters.get("company"):
		frappe.throw(_("Company is required"))


def get_columns(months):
	columns = [
		{"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
		{"label": "Warehouse Name", "fieldname": "warehouse_name", "fieldtype": "Data", "width": 200},
	]
	for label, _ in months:
		columns.append({
			"label": label,
			"fieldname": label,
			"fieldtype": "Float",
			"width": 120,
		})
	return columns


def get_fiscal_months(fiscal_year):
	start_date = frappe.db.get_value("Fiscal Year", fiscal_year, "year_start_date")
	start_date = getdate(start_date)
	months = []
	for i in range(12):
		month_start = add_months(start_date, i)
		opening_balance_date = add_days(month_start, -1)  # Opening as of 1st = last day of previous month
		label = month_start.strftime("%b %Y")
		months.append((label, opening_balance_date))
	return months


def get_valid_warehouses():
	return frappe.get_all(
		"Warehouse",
		filters={"is_group": 0, "disabled": 0},
		fields=["name", "warehouse_name"]
	)


def get_items_under_group(item_group):
	groups = [item_group] + get_descendants_of("Item Group", item_group)
	return frappe.get_all("Item", filters={"item_group": ("in", groups)}, fields=["name"])


def get_stock_qty_from_ledger(item_code, warehouse, date):
	# Use posting_datetime for accuracy
	datetime_end = f"{date} 23:59:59"
	qty = frappe.db.sql("""
		SELECT SUM(actual_qty)
		FROM `tabStock Ledger Entry`
		WHERE item_code = %s
		AND warehouse = %s
		AND posting_datetime <= %s
		AND docstatus < 2
	""", (item_code, warehouse, datetime_end))[0][0]
	return qty or 0

def get_latest_qty_snapshot(item_code, warehouse, date):
	datetime_cutoff = f"{date} 23:59:59"
	result = frappe.db.sql("""
		SELECT qty_after_transaction
		FROM `tabStock Ledger Entry`
		WHERE item_code = %s
		AND warehouse = %s
		AND posting_datetime <= %s
		AND docstatus < 2
		ORDER BY posting_datetime DESC, name DESC
		LIMIT 1
	""", (item_code, warehouse, datetime_cutoff))
	return result[0][0] if result else 0
