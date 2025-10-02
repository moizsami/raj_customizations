import frappe
from frappe.utils import getdate, today

def execute(filters=None):
    filters = filters or {}
    date_str = filters.get("from_date") or today()
    the_date = getdate(date_str)

    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "Shift", "fieldname": "shift", "fieldtype": "Link", "options": "Shift Type", "width": 150},
        {"label": "Check-in Time", "fieldname": "check_in_time", "fieldtype": "Datetime", "width": 170},
    ]

    # first IN on that date; shift = ec.shift OR employee.default_shift
    data = frappe.db.sql(
        """
        SELECT
            ec.employee,
            e.employee_name,
            COALESCE(MIN(ec.shift), e.default_shift) AS shift,
            MIN(ec.time) AS check_in_time
        FROM `tabEmployee Checkin` ec
        LEFT JOIN `tabEmployee` e ON e.name = ec.employee
        WHERE DATE(ec.time) = %(date)s
        GROUP BY ec.employee, e.employee_name, e.default_shift
        ORDER BY MIN(ec.time) ASC
        """,
        {"date": the_date},
        as_dict=True,
    )

    return columns, data
