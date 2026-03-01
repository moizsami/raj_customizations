import frappe
from frappe.utils import getdate, get_datetime, nowdate

@frappe.whitelist()
def has_checkin_today(employee: str) -> int:
    if not employee:
        return 0
    d = getdate(nowdate())
    start = get_datetime(f"{d} 00:00:00")
    end   = get_datetime(f"{d} 23:59:59")

    cnt = frappe.db.count(
        "Employee Checkin",
        filters=[
            ["Employee Checkin", "employee", "=", employee],
            ["Employee Checkin", "time", "between", [start, end]],
        ],
    )
    return 1 if cnt > 0 else 0
