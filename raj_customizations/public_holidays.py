# in apps/your_app/your_app/payroll/holiday_utils.py
import frappe
from frappe.utils import getdate

def set_public_holiday_count(doc, method=None):
    """Set doc.custom_public_holidays to the number of non-weekly-off holidays
    between start_date and end_date (inclusive) for the employee's holiday list."""
    # Ensure required fields exist
    if not (doc.employee and doc.start_date and doc.end_date):
        # If any are missing, set to 0 and exit quietly (prevents Payroll Entry errors)
        doc.custom_public_holidays = 0
        return

    # Normalize date order just in case
    start_date = getdate(doc.start_date)
    end_date = getdate(doc.end_date)
    if end_date < start_date:
        start_date, end_date = end_date, start_date

    # Get employee's holiday list
    holiday_list = frappe.db.get_value("Employee", doc.employee, "holiday_list")
    if not holiday_list:
        doc.custom_public_holidays = 0
        return

    # Count Holiday child rows where:
    # - parent = holiday_list (child table parent)
    # - weekly_off = 0 (i.e., *public* holidays)
    # - holiday_date in [start_date, end_date] inclusive
    count = frappe.db.sql(
        """
        SELECT COUNT(*)
        FROM `tabHoliday`
        WHERE parent = %s
          AND parenttype = 'Holiday List'
          AND IFNULL(weekly_off, 0) = 0
          AND holiday_date BETWEEN %s AND %s
        """,
        (holiday_list, start_date, end_date),
    )[0][0]

    # Write back to the Salary Slip field
    # (make sure you have created an Int field named custom_public_holidays on Salary Slip)
    doc.custom_public_holidays = int(count)
