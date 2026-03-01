# Script Report for Commission Calculation
import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Sales Person"), "fieldname": "sales_person", "fieldtype": "Link", "options": "Sales Person", "width": 150},
        {"label": _("Sales Invoice ID"), "fieldname": "sales_invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 150},
        {"label": _("Customer"), "fieldname": "customer_name", "fieldtype": "Link", "options": "Customer", "width": 300},
        #{"label": _("Total Sales Amount"), "fieldname": "total_sales_amount", "fieldtype": "Currency", "width": 150},
        {"label": _("Calculated Commission"), "fieldname": "calculated_commission", "fieldtype": "Currency", "width": 150},
    ]

def get_data(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    sales_persons = filters.get("customer_group")

    # Get logged-in user's associated Sales Person
    user_sales_person = frappe.db.get_value("Sales Person", {"custom_user": frappe.session.user}, "name")

    # Superusers or Admins should see all salespersons
    allowed_to_see_all = "Admin Commission Reports" in frappe.get_roles(frappe.session.user)

    # Restrict user from seeing other Sales Persons if they are not allowed
    if not allowed_to_see_all and sales_persons and sales_persons != user_sales_person:
        return []  # Return empty data if unauthorized

    invoices = frappe.db.sql("""
    SELECT 
        si.name AS sales_invoice,
        si.customer_name AS customer_name,
         
        si.customer_group AS sales_person
    FROM 
        `tabSales Invoice` si
    INNER JOIN 
        `tabCustomer` c ON si.customer = c.name
    WHERE 
        si.docstatus = 1
        AND si.customer_group = %(sales_persons)s 
        AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND (c.custom_include_in_commission = '' OR c.custom_include_in_commission is null OR c.custom_include_in_commission = 'Yes')
""", {"sales_persons": sales_persons, "from_date": from_date, "to_date": to_date}, as_dict=True)

    results = []
    for invoice in invoices:
        commission_rule_name = frappe.db.get_value(
            "Sales Person", {"name": invoice.sales_person}, "custom_commission_rule"
        )
        if not commission_rule_name:
            continue  # Skip if no commission rule is found

        commission_rule = frappe.get_doc("Commission Rules", commission_rule_name)
        total_commission = 0

        items = frappe.db.sql("""
            SELECT sii.item_code, sii.item_group, sii.qty, sii.amount
            FROM `tabSales Invoice Item` sii
            WHERE sii.parent = %(sales_invoice)s
        """, {"sales_invoice": invoice.sales_invoice}, as_dict=True)

        for item in items:
            commission_entry = next(
                (row for row in commission_rule.item_commission if row.item == item.item_code),
                None
            )
            if not commission_entry:
                commission_entry = next(
                    (row for row in commission_rule.item_group_commission if row.item_group == item.item_group),
                    None
                )
            if commission_entry:
                commission_type = commission_entry.commission_type
                if commission_type == "Qty":
                    total_commission += item.qty * commission_entry.commission_rate_egp
                elif commission_type == "Kg" and commission_entry.item_group == "الوان ميتالك":
                    weight_per_unit = frappe.db.get_value("Item", item.item_code, "weight_per_unit") or 0
                    if not weight_per_unit or weight_per_unit == 0:
                        # If weight is missing or zero, fallback to qty * rate
                        total_commission += (item.qty or 0) * commission_entry.commission_rate_egp
                    else:
                        total_weight = weight_per_unit * (item.qty or 0)
                        total_commission += total_weight * commission_entry.commission_rate_egp
                elif commission_type == "Tax Deducted Amount":
                    total_commission += calculate_tax_deducted_commission(
                        item.amount, commission_entry.commission_percent
                    )

        results.append({
            "sales_person": invoice.sales_person,
            "sales_invoice": invoice.sales_invoice,
            "customer_name": invoice.customer_name,
            #"total_sales_amount": invoice.total_sales_amount,
            "calculated_commission": total_commission,
        })

    return results

def calculate_tax_deducted_commission(amount, commission_percent):
    cal_a_two = amount * 1.14  # Add 14%
    #yearly = cal_a_two * 0.0025  # Yearly contribution
    tax = cal_a_two * 0.15  # Tax
    net_amount = cal_a_two - tax
    return net_amount * (commission_percent / 100)