import frappe
from frappe.utils import getdate, add_days, flt

# --- config ---
PRESENT_STATUSES = {"Present"}         # add "Half Day", "Work From Home" if you want
WEEK_START_DOW   = 5                   # Saturday (Mon=0..Sun=6)
DEDUCT_COMPONENT = "خصم الحوافز"       # must exist as a Deduction Salary Component
MONTHLY_MAX_DEDUCT = 800               # cap

# ---------- calc helpers ----------
# --- SSA guard: only run if the latest submitted SSA has variable > 0 ---
def _ssa_variable_gt_zero(employee, as_of_date, fieldname="variable"):
    """Return True iff the most recent submitted SSA (from_date <= as_of_date)
    has the numeric field 'fieldname' > 0.  Adjust fieldname if your site uses a custom one
    (e.g. 'custom_variable')."""
    row = frappe.db.sql(
        """
        SELECT {fn} AS varval
        FROM `tabSalary Structure Assignment`
        WHERE employee=%s AND docstatus=1 AND from_date <= %s
        ORDER BY from_date DESC
        LIMIT 1
        """.format(fn=frappe.db.escape(fieldname, percent=False)),
        (employee, as_of_date),
        as_dict=True,
    )
    if not row:
        return False
    return flt(row[0].get("varval")) > 0


def _remove_deduction_row(doc, component_name):
    """Helper to clean up if the employee no longer qualifies."""
    for r in list(doc.get("deductions") or []):
        if r.salary_component == component_name:
            doc.remove(r)
    # also keep your reference field in sync if you use one
    if hasattr(doc, "custom_weekly_absence_deduction"):
        doc.set("custom_weekly_absence_deduction", 0)


def _prev_or_same_saturday(d):
    d = getdate(d)
    back = (d.weekday() - WEEK_START_DOW) % 7
    return add_days(d, -back)

def _present_dates(employee, start_date, end_date):
    rows = frappe.db.get_all(
        "Attendance",
        filters={"employee": employee, "attendance_date": ["between", [start_date, end_date]]},
        fields=["attendance_date", "status"],
    )
    return {
        getdate(r.attendance_date)
        for r in rows
        if (r.status or "").strip() in PRESENT_STATUSES
    }

def _holiday_dates(employee, start_date, end_date):
    emp = frappe.db.get_value("Employee", employee, ["holiday_list", "company"], as_dict=True)
    if not emp:
        return set()
    hlist = emp.holiday_list or frappe.db.get_value("Company", emp.company, "default_holiday_list")
    if not hlist:
        return set()
    hols = frappe.db.get_all(
        "Holiday",
        filters={"parenttype": "Holiday List", "parent": hlist, "holiday_date": ["between", [start_date, end_date]]},
        pluck="holiday_date",
    )
    return {getdate(h) for h in hols}

def _week_working_days(week_start, holidays):
    # Sat→Thu (skip Friday), minus holidays
    days = []
    for off in range(7):
        d = add_days(week_start, off)
        if d.weekday() == 4:  # Friday
            continue
        if d in holidays:
            continue
        days.append(d)
    return days

def _deduction_for_week(working_days, present_dates):
    absent = sum(1 for d in working_days if d not in present_dates)
    if absent == 1:
        return 100
    elif absent >= 2:
        return 200
    return 0

def calculate_weekly_deduction(employee, payroll_start, payroll_end):
    """Exactly 4 Sat→Thu weeks, anchored to prev/same Saturday of payroll_start."""
    s0 = _prev_or_same_saturday(payroll_start)
    s4 = add_days(s0, 28)
    end_inclusive = add_days(s4, -1)

    present = _present_dates(employee, s0, end_inclusive)
    holidays = _holiday_dates(employee, s0, end_inclusive)

    total = 0
    for i in range(4):
        wk_start = add_days(s0, i * 7)
        working_days = _week_working_days(wk_start, holidays)
        total += _deduction_for_week(working_days, present)

    return min(total, MONTHLY_MAX_DEDUCT)

# ---------- table + totals helpers ----------
def _upsert_deduction_row(doc, component_name, amount):
    """Create/update a single deduction row by component; remove duplicates; set amounts."""
    amount = flt(amount, 2)

    # try to find existing row
    existing = None
    dupes = []
    for row in doc.get("deductions", []):
        if row.salary_component == component_name:
            if existing is None:
                existing = row
            else:
                dupes.append(row)

    # remove any duplicate rows to avoid double counting
    for r in dupes:
        doc.remove(r)

    if amount <= 0:
        # if zero and exists, remove it
        if existing:
            doc.remove(existing)
        return

    if existing:
        existing.amount = amount
        # keep default_amount in sync if you use it
        if hasattr(existing, "default_amount"):
            existing.default_amount = amount
    else:
        newr = doc.append("deductions", {})
        newr.salary_component = component_name
        newr.amount = amount
        if hasattr(newr, "default_amount"):
            newr.default_amount = amount

def _recompute_totals(doc):
    """Recompute totals so the draft shows correct figures immediately."""
    gross = sum(flt(e.amount) for e in (doc.get("earnings") or []))
    deduct = sum(flt(d.amount) for d in (doc.get("deductions") or []))
    doc.gross_pay = flt(gross, 2)
    doc.total_deduction = flt(deduct, 2)
    doc.net_pay = flt(doc.gross_pay - doc.total_deduction, 2)
    # If your site uses base_* fields and rounding, you can also set:
    # doc.base_gross_pay = doc.gross_pay
    # doc.base_total_deduction = doc.total_deduction
    # doc.base_net_pay = doc.net_pay

# ---------- main hook ----------
def apply_weekly_deduction(doc, method):
    """
    Register this on BOTH 'before_validate' and 'before_save' for Salary Slip.
    - Compute monthly absence deduction (Sat→Thu, 4 weeks).
    - Store it in custom field (for reference) AND inject a deduction row.
    - Recompute totals so payroll-generated drafts show it immediately.
    """

    # --- filter by salary structure ---
    if doc.salary_structure != "Workers Monthly 2025 v2":
        return  # exit early, do nothing

    # determine payroll window just to anchor the month
    payroll_start = payroll_end = None
    if getattr(doc, "payroll_entry", None):
        pe = frappe.get_value("Payroll Entry", doc.payroll_entry, ["start_date", "end_date"], as_dict=True)
        if pe:
            payroll_start, payroll_end = pe.start_date, pe.end_date
    if not payroll_start:
        payroll_start = getattr(doc, "start_date", None) or getattr(doc, "posting_date", None)
    if not payroll_end:
        payroll_end = getattr(doc, "end_date", None) or getattr(doc, "posting_date", None)

    if not (payroll_start and payroll_end):
        # fallback: do nothing rather than corrupt totals
        return

    total = calculate_weekly_deduction(doc.employee, payroll_start, payroll_end)

    # keep the reference field (and trigger any formula watchers that DO listen)
    doc.set("custom_weekly_absence_deduction", total)

    # force it into deductions table so it shows up in draft slips from payroll
    _upsert_deduction_row(doc, DEDUCT_COMPONENT, total)

    # recompute totals right now (since we're after core validate when generating from payroll)
    _recompute_totals(doc)
