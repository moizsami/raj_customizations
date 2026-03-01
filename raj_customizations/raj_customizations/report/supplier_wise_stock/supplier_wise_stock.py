# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": _("Warehouse"),
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 150
        },
        {
            "label": _("Current Stock"),
            "fieldname": "current_stock",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("UOM"),
            "fieldname": "uom",
            "fieldtype": "Link",
            "options": "UOM",
            "width": 80
        },
        {
            "label": _("Supplier"),
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 180
        },
        {
            "label": _("Supplier Qty"),
            "fieldname": "supplier_qty",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("Valuation Rate"),
            "fieldname": "valuation_rate",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Stock Value"),
            "fieldname": "stock_value",
            "fieldtype": "Currency",
            "width": 130
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    # Get current stock balances
    stock_data = frappe.db.sql("""
        SELECT 
            sle.item_code,
            item.item_name,
            sle.warehouse,
            SUM(sle.actual_qty) as current_stock,
            item.stock_uom as uom,
            sle.valuation_rate
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` item ON sle.item_code = item.name
        WHERE sle.docstatus = 1
        {conditions}
        GROUP BY sle.item_code, sle.warehouse
        HAVING SUM(sle.actual_qty) > 0
        ORDER BY sle.item_code, sle.warehouse
    """.format(conditions=conditions), filters, as_dict=1)
    
    result = []
    
    for stock in stock_data:
        # Get supplier-wise breakdown for this item-warehouse combination
        supplier_breakdown = get_supplier_breakdown(
            stock.item_code, 
            stock.warehouse,
            stock.current_stock
        )
        
        if supplier_breakdown:
            for supplier_data in supplier_breakdown:
                stock_value = supplier_data['supplier_qty'] * stock.valuation_rate
                result.append({
                    'item_code': stock.item_code,
                    'item_name': stock.item_name,
                    'warehouse': stock.warehouse,
                    'current_stock': stock.current_stock,
                    'uom': stock.uom,
                    'supplier': supplier_data['supplier'],
                    'supplier_qty': supplier_data['supplier_qty'],
                    'valuation_rate': stock.valuation_rate,
                    'stock_value': stock_value
                })
        else:
            # If no supplier found, show as Non-Supplier Stock
            stock_value = stock.current_stock * stock.valuation_rate
            result.append({
                'item_code': stock.item_code,
                'item_name': stock.item_name,
                'warehouse': stock.warehouse,
                'current_stock': stock.current_stock,
                'uom': stock.uom,
                'supplier': 'Non-Supplier Stock',
                'supplier_qty': stock.current_stock,
                'valuation_rate': stock.valuation_rate,
                'stock_value': stock_value
            })
    
    return result

def get_supplier_breakdown(item_code, warehouse, total_qty):
    """
    Trace back stock to suppliers using FIFO logic
    """
    # Get all incoming stock entries with supplier info
    incoming_stock = frappe.db.sql("""
        SELECT 
            sle.name,
            sle.posting_date,
            sle.posting_time,
            sle.actual_qty,
            sle.voucher_type,
            sle.voucher_no,
            CASE 
                WHEN sle.voucher_type = 'Purchase Receipt' THEN pr.supplier
                WHEN sle.voucher_type = 'Purchase Invoice' THEN pi.supplier
                ELSE NULL
            END as supplier
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabPurchase Receipt` pr ON sle.voucher_type = 'Purchase Receipt' AND sle.voucher_no = pr.name
        LEFT JOIN `tabPurchase Invoice` pi ON sle.voucher_type = 'Purchase Invoice' AND sle.voucher_no = pi.name
        WHERE 
            sle.item_code = %(item_code)s
            AND sle.warehouse = %(warehouse)s
            AND sle.actual_qty > 0
            AND sle.docstatus = 1
        ORDER BY sle.posting_date, sle.posting_time, sle.creation
    """, {'item_code': item_code, 'warehouse': warehouse}, as_dict=1)
    
    # Get all outgoing stock entries
    outgoing_stock = frappe.db.sql("""
        SELECT 
            sle.posting_date,
            sle.posting_time,
            ABS(sle.actual_qty) as actual_qty
        FROM `tabStock Ledger Entry` sle
        WHERE 
            sle.item_code = %(item_code)s
            AND sle.warehouse = %(warehouse)s
            AND sle.actual_qty < 0
            AND sle.docstatus = 1
        ORDER BY sle.posting_date, sle.posting_time, sle.creation
    """, {'item_code': item_code, 'warehouse': warehouse}, as_dict=1)
    
    # Apply FIFO to determine remaining stock by supplier
    remaining_incoming = []
    for inc in incoming_stock:
        remaining_incoming.append({
            'supplier': inc.supplier or 'Non-Supplier Stock',
            'qty': inc.actual_qty,
            'posting_date': inc.posting_date,
            'posting_time': inc.posting_time
        })
    
    # Deduct outgoing stock from incoming (FIFO)
    for outgoing in outgoing_stock:
        qty_to_deduct = outgoing.actual_qty
        
        for incoming in remaining_incoming:
            if qty_to_deduct <= 0:
                break
            
            if incoming['qty'] > 0:
                deduction = min(incoming['qty'], qty_to_deduct)
                incoming['qty'] -= deduction
                qty_to_deduct -= deduction
    
    # Group by supplier
    supplier_qty = {}
    for inc in remaining_incoming:
        if inc['qty'] > 0:
            supplier = inc['supplier']
            supplier_qty[supplier] = supplier_qty.get(supplier, 0) + inc['qty']
    
    # Convert to list format
    result = []
    for supplier, qty in supplier_qty.items():
        result.append({
            'supplier': supplier,
            'supplier_qty': qty
        })
    
    # Sort: Suppliers first, then Non-Supplier Stock
    result.sort(key=lambda x: (x['supplier'] == 'Non-Supplier Stock', x['supplier']))
    
    return result

def get_conditions(filters):
    conditions = ""
    
    if filters.get("item_code"):
        conditions += " AND sle.item_code = %(item_code)s"
    
    if filters.get("warehouse"):
        conditions += " AND sle.warehouse = %(warehouse)s"
    
    if filters.get("item_group"):
        conditions += " AND item.item_group = %(item_group)s"
    
    return conditions