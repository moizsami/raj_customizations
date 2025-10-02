import frappe
from frappe.utils import flt, getdate, add_days


def _get_ssa_pay_buckets(employee, as_of_date):
    """Return (base, custom_badal_wagba) from the most recent submitted
    Salary Structure Assignment effective on or before as_of_date.
    If custom_badal_wagba is missing/NULL, treat it as 0.
    """
    rows = frappe.db.sql(
        """
        SELECT
            base,
            COALESCE(custom_badal_wagba, 0) AS custom_badal_wagba
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

    if not rows:
        frappe.throw("No submitted Salary Structure Assignment found for this employee.")

    base = flt(rows[0].get("base"))
    if not base:
        frappe.throw("The Salary Structure Assignment has no value in the 'base' field.")

    badal = flt(rows[0].get("custom_badal_wagba") or 0)
    return base, badal


def apply_weekly_overtime(doc, method=None):
    if not doc.start_date or not doc.end_date:
        frappe.throw("Start Date and End Date are required to calculate overtime.")

    holiday_list = frappe.db.get_value("Employee", doc.employee, "holiday_list")
    if not holiday_list:
        frappe.throw("Employee does not have a Holiday List assigned.")

    start_date = getdate(doc.start_date)
    end_date = getdate(doc.end_date)

    # Pull both base and custom_badal_wagba from the effective SSA
    ssa_base, ssa_badal_wagba = _get_ssa_pay_buckets(doc.employee, end_date)

    # Count qualifying overtime days (Present on a Holiday that is a Friday)
    overtime_days = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == 4:  # Friday
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

    # Overtime formula on base: (base/26)*2 * days
    per_day_overtime = (ssa_base / 26.0) * 2.0
    overtime_amount = flt(overtime_days * per_day_overtime, 2)

    # Add daily "badal wagba" per overtime day, then sum with overtime_amount
    badal_total = flt(ssa_badal_wagba * overtime_days, 2)

    # Final combined overtime = base-derived + badal wagba
    combined_overtime = flt(overtime_amount + badal_total, 2)

    # Upsert single earning row
    target_component = "راتب العمل الإضافي"
    found = False
    for row in (doc.earnings or []):
        if row.salary_component == target_component:
            row.amount = combined_overtime
            found = True
            break

    if not found and combined_overtime:
        doc.append("earnings", {
            "salary_component": target_component,
            "amount": combined_overtime
        })

    # (Optional) If you want to expose details for auditing/debugging, uncomment:
    # doc.db_set("custom_overtime_days", overtime_days, update_modified=False)
    # doc.db_set("custom_overtime_base_amount", overtime_amount, update_modified=False)
    # doc.db_set("custom_overtime_badal_total", badal_total, update_modified=False)
