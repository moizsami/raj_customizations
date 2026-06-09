# Copyright (c) 2026, moiz@samtech-solutions.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Sales Person"), "fieldname": "sales_person", "fieldtype": "Data", "width": 150},
        {"label": _("Sales Invoice ID"), "fieldname": "sales_invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 150},
        {"label": _("Customer"), "fieldname": "customer_name", "fieldtype": "Link", "options": "Customer", "width": 300},
        {"label": _("Calculated Commission"), "fieldname": "calculated_commission", "fieldtype": "Currency", "width": 150},
    ]

def get_data(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    sales_persons = filters.get("customer_group")

    user_sales_person = frappe.db.get_value("Sales Person", {"custom_user": frappe.session.user}, "name")
    allowed_to_see_all = "Admin Commission Reports" in frappe.get_roles(frappe.session.user)

    if not allowed_to_see_all and sales_persons and sales_persons != user_sales_person:
        return []

    # Clear document cache to avoid stale data across refreshes
    frappe.local.document_cache = {}

    # Fetch commission rule ONCE for this sales person
    commission_rule = None
    commission_rule_name = frappe.db.get_value(
        "Sales Person", {"name": sales_persons}, "custom_commission_rule"
    ) if sales_persons else None

    if commission_rule_name:
        commission_rule = frappe.get_doc("Commission Rules", commission_rule_name)

    if not commission_rule:
        return []

    results = []

    # ── PART 1: Own invoices ─────────────────────────────────────────────────
    own_invoices = frappe.db.sql("""
        SELECT 
            si.name AS sales_invoice,
            si.customer_name AS customer_name,
            si.customer_group AS sales_person
        FROM `tabSales Invoice` si
        INNER JOIN `tabCustomer` c ON si.customer = c.name
        WHERE 
            si.docstatus = 1
            AND si.customer_group = %(sales_persons)s
            AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND (c.custom_include_in_commission = '' OR c.custom_include_in_commission IS NULL OR c.custom_include_in_commission = 'Yes')
        ORDER BY si.posting_date ASC, si.name ASC
    """, {"sales_persons": sales_persons, "from_date": from_date, "to_date": to_date}, as_dict=True)

    for invoice in own_invoices:
        items = frappe.db.sql("""
            SELECT sii.item_code, sii.item_group, sii.qty, sii.amount
            FROM `tabSales Invoice Item` sii
            WHERE sii.parent = %(sales_invoice)s
        """, {"sales_invoice": invoice.sales_invoice}, as_dict=True)

        total_commission = 0
        for item in items:
            # First try matching by item_code in item_commission table
            commission_entry = next(
                (row for row in commission_rule.item_commission if row.item == item.item_code),
                None
            )
            # Fallback to item_group_commission table
            if not commission_entry:
                commission_entry = next(
                    (row for row in commission_rule.item_group_commission if row.item_group == item.item_group),
                    None
                )
            if commission_entry:
                total_commission += calculate_commission_for_entry(item, commission_entry)

        results.append({
            "sales_person": invoice.sales_person,
            "sales_invoice": invoice.sales_invoice,
            "customer_name": invoice.customer_name,
            "calculated_commission": total_commission,
        })

    # ── PART 2: Other sales persons' invoices (helper commission) ────────────
    if commission_rule.add_commission_for_other_sales_invoices and \
       commission_rule.items_for_other_sales_invoices:

        other_invoices = frappe.db.sql("""
            SELECT 
                si.name AS sales_invoice,
                si.customer_name AS customer_name,
                si.customer_group AS sales_person
            FROM `tabSales Invoice` si
            INNER JOIN `tabCustomer` c ON si.customer = c.name
            WHERE 
                si.docstatus = 1
                AND si.customer_group != %(sales_persons)s
                AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
                AND (c.custom_include_in_commission = '' OR c.custom_include_in_commission IS NULL OR c.custom_include_in_commission = 'Yes')
            ORDER BY si.posting_date ASC, si.name ASC
        """, {"sales_persons": sales_persons, "from_date": from_date, "to_date": to_date}, as_dict=True)

        for invoice in other_invoices:
            items = frappe.db.sql("""
                SELECT sii.item_code, sii.item_group, sii.qty, sii.amount
                FROM `tabSales Invoice Item` sii
                WHERE sii.parent = %(sales_invoice)s
            """, {"sales_invoice": invoice.sales_invoice}, as_dict=True)

            total_commission = 0
            for item in items:
                # Match only against the helper items table
                commission_entry = next(
                    (row for row in commission_rule.items_for_other_sales_invoices
                     if row.item == item.item_code),
                    None
                )
                if commission_entry:
                    total_commission += calculate_commission_for_entry(item, commission_entry)

            # Only append rows where commission was actually earned
            if total_commission > 0:
                results.append({
                    "sales_person": invoice.sales_person,
                    "sales_invoice": invoice.sales_invoice,
                    "customer_name": invoice.customer_name,
                    "calculated_commission": total_commission,
                })

    return results


def calculate_commission_for_entry(item, commission_entry):
    commission_type = commission_entry.commission_type

    if commission_type == "Qty":
        return (item.qty or 0) * commission_entry.commission_rate_egp

    elif commission_type == "Kg" and commission_entry.get("item_group") == "الوان ميتالك":
        weight_per_unit = frappe.db.get_value("Item", item.item_code, "weight_per_unit") or 0
        if not weight_per_unit:
            return (item.qty or 0) * commission_entry.commission_rate_egp
        return weight_per_unit * (item.qty or 0) * commission_entry.commission_rate_egp

    elif commission_type == "Tax Deducted Amount":
        return calculate_tax_deducted_commission(item.amount, commission_entry.commission_percent)

    return 0


def calculate_tax_deducted_commission(amount, commission_percent):
    cal_a_two = amount * 1.14
    tax = cal_a_two * 0.15
    net_amount = cal_a_two - tax
    return net_amount * (commission_percent / 100)




@frappe.whitelist()
def get_total_commission(from_date, to_date, sales_person):
    filters = {
        "from_date": from_date,
        "to_date": to_date,
        "customer_group": sales_person
    }
    
    # Temporarily switch user to Administrator to bypass role permission check in get_data
    original_user = frappe.session.user
    try:
        frappe.set_user("Administrator")
        data = get_data(filters)
    finally:
        frappe.set_user(original_user)
        
    # Sum up the calculated commission from all retrieved rows
    total_commission = sum(row.get("calculated_commission", 0) for row in data)
    return total_commission
