# Copyright (c) 2026, moiz@samtech-solutions.com and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"label": "Current Qty", "fieldname": "current_qty", "fieldtype": "Float", "width": 110},
        {"label": "Rate", "fieldname": "price_list_rate", "fieldtype": "Currency", "width": 120},
        {"label": "Stock Value (Sales)", "fieldname": "stock_value", "fieldtype": "Currency", "width": 150},
    ]

def get_data(filters):
    if not filters.get("price_list"):
        frappe.throw("Please select a Price List")

    conditions = get_conditions(filters)

    bin_data = frappe.db.sql(f"""
        SELECT
            bin.item_code,
            item.item_name,
            bin.warehouse,
            bin.actual_qty AS current_qty
        FROM `tabBin` bin
        INNER JOIN `tabItem` item ON item.name = bin.item_code
        WHERE bin.actual_qty > 0 {conditions}
        ORDER BY bin.item_code
    """, filters, as_dict=1)

    item_codes = list({d.item_code for d in bin_data})
    item_prices = {}

    if item_codes:
        price_data = frappe.db.sql("""
            SELECT item_code, price_list_rate
            FROM `tabItem Price`
            WHERE price_list = %s
                AND selling = 1
                AND item_code IN %s
        """, (filters.get("price_list"), item_codes), as_dict=1)

        for p in price_data:
            item_prices[p.item_code] = p.price_list_rate

    data = []
    total_qty = 0
    total_value = 0

    for row in bin_data:
        rate = item_prices.get(row.item_code, 0) or 0
        stock_value = rate * row.current_qty

        row["price_list_rate"] = rate
        row["stock_value"] = stock_value

        total_qty += row.current_qty
        total_value += stock_value
        data.append(row)

    return data

def get_conditions(filters):
    conditions = ""
    if filters.get("item_group"):
        conditions += " AND item.item_group = %(item_group)s"
    if filters.get("warehouse"):
        conditions += " AND bin.warehouse = %(warehouse)s"
    return conditions






