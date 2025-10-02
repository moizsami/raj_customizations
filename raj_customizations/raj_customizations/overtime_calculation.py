import frappe
from frappe.utils import flt, getdate, add_days

def _get_ssa_base(employee, as_of_date):
    """Return the 'base' from the most recent submitted Salary Structure Assignment
    effective on or before as_of_date."""
    row = frappe.db.sql(
        """
        SELECT base
        FROM `tabSalary Structure Assignment`
        WHERE employee = %s
          AND docstatus = 1
          AND from_date <= %s
        ORDER BY from_date DESC
        LIMIT 1
        """,
        (employee, as_of_date),
        as_dict=True,
    )
    if not row:
        frappe.throw("No submitted Salary Structure Assignment found for this employee.")
    base = flt(row[0].get("base"))
    if not base:
        frappe.throw("The Salary Structure Assignment has no value in the 'base' field.")
    return base

def apply_weekly_overtime(doc, method=None):
    if not doc.start_date or not doc.end_date:
        frappe.throw("Start Date and End Date are required to calculate overtime.")

    holiday_list = frappe.db.get_value("Employee", doc.employee, "holiday_list")
    if not holiday_list:
        frappe.throw("Employee does not have a Holiday List assigned.")

    # Use the assignment effective by the end_date (adjust if you prefer start_date)
    start_date = getdate(doc.start_date)
    end_date = getdate(doc.end_date)
    ssa_base = _get_ssa_base(doc.employee, end_date)

    # Count qualifying overtime days (Present on a Holiday that is a Friday)
    overtime_days = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == 4:  # Friday (Mon=0 ... Sun=6)
            is_holiday = frappe.db.exists("Holiday", {
                "holiday_date": current_date,
                "parent": holiday_list
            })
            if is_holiday:
                is_present = frappe.db.exists("Attendance", {
                    "employee": doc.employee,
                    "attendance_date": current_date,
                    "status": "Present"
                })
                if is_present:
                    overtime_days += 1
        current_date = add_days(current_date, 1)

    # Overtime formula: (base/26)*2 * days
    per_day_overtime = (ssa_base / 26.0) * 2.0
    overtime_amount = flt(overtime_days * per_day_overtime, 2)

    # Upsert "Over Time" earning
    found = False
    for row in doc.earnings or []:
        if row.salary_component == "راتب العمل الإضافي":
            row.amount = overtime_amount
            found = True
            break

    if not found and overtime_amount:
        doc.append("earnings", {
            "salary_component": "راتب العمل الإضافي",
            "amount": overtime_amount
        })
