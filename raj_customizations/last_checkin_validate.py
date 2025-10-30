# your_app/your_app/hr/salary_slip_hooks.py
import frappe
from frappe.utils import getdate, get_datetime, nowdate

def _has_checkin_today(employee: str) -> bool:
    if not employee:
        return False

    # Site-local "today" boundaries
    d = getdate(nowdate())
    start = get_datetime(f"{d} 00:00:00")
    end   = get_datetime(f"{d} 23:59:59")

    return frappe.db.count(
        "Employee Checkin",
        filters=[
            ["Employee Checkin", "employee", "=", employee],
            ["Employee Checkin", "time", "between", [start, end]],
        ],
    ) > 0

def set_last_day_checkin_flag(doc, method=None):
    """Runs on Salary Slip validate (both manual and via Payroll Entry)."""
    try:
        doc.custom_last_day_checkin = 1 if _has_checkin_today(doc.employee) else 0
    except Exception:
        # Be defensive: never block slip creation because of this flag
        doc.custom_last_day_checkin = 0
