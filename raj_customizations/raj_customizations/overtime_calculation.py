import frappe
from frappe.utils import flt, getdate, add_days

def _get_ssa_pay_buckets(employee, as_of_date):
    """Return (base, custom_badal_wagba) from the most recent submitted SSA."""
    rows = frappe.db.sql(
        """
        SELECT base, COALESCE(custom_badal_wagba, 0) AS custom_badal_wagba
        FROM `tabSalary Structure Assignment`
        WHERE employee = %s AND docstatus = 1 AND from_date <= %s
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
    """
    Counts overtime days as:
      - Any **Friday weekly off** that appears in the employee's Holiday List (weekly_off = 1), AND employee is Present.
      - Any **official public holiday** in the Holiday List (weekly_off = 0), AND employee is Present.

    For each such day:
      Overtime = (base/26)*2  +  custom_badal_wagba

    Adds/updates a single earning row: "راتب العمل الإضافي".
    """
    if not doc.start_date or not doc.end_date:
        frappe.throw("Start Date and End Date are required to calculate overtime.")

    holiday_list = frappe.db.get_value("Employee", doc.employee, "holiday_list")
    if not holiday_list:
        frappe.throw("Employee does not have a Holiday List assigned.")

    start_date = getdate(doc.start_date)
    end_date = getdate(doc.end_date)

    # Pull both base and custom_badal_wagba from the effective SSA
    ssa_base, ssa_badal_wagba = _get_ssa_pay_buckets(doc.employee, end_date)

    # --- Prefetch Holidays (weekly off vs public holiday) in one shot ---
    holidays = frappe.get_all(
        "Holiday",
        filters={
            "parent": holiday_list,
            "holiday_date": ["between", [start_date, end_date]],
        },
        fields=["holiday_date", "weekly_off"],
        pluck=None,
    )

    friday_weekly_off_dates = set()
    public_holiday_dates = set()

    for h in holidays:
        hdate = getdate(h["holiday_date"])
        if int(h.get("weekly_off") or 0) == 1:
            # Treat as weekly off (commonly Fridays in Egypt)
            friday_weekly_off_dates.add(hdate)
        else:
            # Official public holiday (weekly_off = 0)
            public_holiday_dates.add(hdate)

    # --- Prefetch Present attendances for the employee in the window ---
    present_att = frappe.get_all(
        "Attendance",
        filters={
            "employee": doc.employee,
            "attendance_date": ["between", [start_date, end_date]],
            "status": "Present",
        },
        fields=["attendance_date"],
        pluck="attendance_date",
    )
    present_dates = {getdate(d) for d in present_att}

    # Qualifying overtime days:
    # 1) Friday weekly off days the employee worked
    # 2) Official public holidays (weekly_off = 0) the employee worked
    qualifying_overtime_dates = (friday_weekly_off_dates | public_holiday_dates) & present_dates
    overtime_days = len(qualifying_overtime_dates)

    # Overtime formula on base: (base/26)*2 * days
    per_day_overtime = (ssa_base / 26.0) * 2.0
    overtime_amount = flt(overtime_days * per_day_overtime, 2)

    # Add daily "badal wagba" per overtime day
    badal_total = flt(ssa_badal_wagba * overtime_days, 2)

    # Final combined overtime
    combined_overtime = flt(overtime_amount + badal_total, 2)

    # Upsert single earning row
    target_component = "راتب العمل الإضافي"
    found = False
    for row in (doc.earnings or []):
        if row.salary_component == target_component:
            row.amount = flt(row.amount) + combined_overtime
            found = True
            break

    if not found and combined_overtime:
        doc.append("earnings", {
            "salary_component": target_component,
            "amount": combined_overtime
        })

    # Optional debug fields if you have them:
    # doc.db_set("custom_overtime_days", overtime_days, update_modified=False)
    # doc.db_set("custom_overtime_base_amount", overtime_amount, update_modified=False)
    # doc.db_set("custom_overtime_badal_total", badal_total, update_modified=False)
