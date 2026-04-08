import frappe
from frappe.utils import getdate, get_first_day, get_last_day, today


def execute(filters=None):
    filters = filters or {}

    from_date = getdate(filters.get("from_date") or get_first_day(today()))
    to_date = getdate(filters.get("to_date") or get_last_day(today()))

    account_type = filters.get("account_type") or None

    columns = get_columns()
    data = get_data(from_date, to_date, account_type)
    return columns, data


def get_columns():
    return [
        {
            "label": "Account",
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 220,
        },
        {
            "label": "Type",
            "fieldname": "account_type",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Opening Balance",
            "fieldname": "opening_balance",
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "label": "Debit (Period)",
            "fieldname": "period_debit",
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "label": "Credit (Period)",
            "fieldname": "period_credit",
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "label": "Closing Balance",
            "fieldname": "closing_balance",
            "fieldtype": "Currency",
            "width": 150,
        },
    ]


def get_data(from_date, to_date, account_type=None):
    type_condition = "AND ac.account_type = %(account_type)s" if account_type else "AND ac.account_type IN ('Cash', 'Bank')"

    # Opening: all GL entries strictly before from_date
    opening_data = frappe.db.sql(
        f"""
        SELECT
            gl.account,
            ac.account_type,
            SUM(gl.debit) - SUM(gl.credit) AS opening_balance
        FROM `tabGL Entry` gl
        INNER JOIN `tabAccount` ac ON ac.name = gl.account
        WHERE ac.disabled = 0
          {type_condition}
          AND gl.is_cancelled = 0
          AND gl.posting_date < %(from_date)s
        GROUP BY gl.account, ac.account_type
        """,
        {"from_date": from_date, "account_type": account_type},
        as_dict=True,
    )

    # Period movements: GL entries within from_date to to_date
    period_data = frappe.db.sql(
        f"""
        SELECT
            gl.account,
            ac.account_type,
            SUM(gl.debit)  AS period_debit,
            SUM(gl.credit) AS period_credit
        FROM `tabGL Entry` gl
        INNER JOIN `tabAccount` ac ON ac.name = gl.account
        WHERE ac.disabled = 0
          {type_condition}
          AND gl.is_cancelled = 0
          AND gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY gl.account, ac.account_type
        """,
        {"from_date": from_date, "to_date": to_date, "account_type": account_type},
        as_dict=True,
    )

    # Merge into a single dict keyed by account
    result = {}

    for row in opening_data:
        result[row.account] = {
            "account": row.account,
            "account_type": row.account_type,
            "opening_balance": row.opening_balance or 0,
            "period_debit": 0,
            "period_credit": 0,
            "closing_balance": 0,
        }

    for row in period_data:
        if row.account not in result:
            result[row.account] = {
                "account": row.account,
                "account_type": row.account_type,
                "opening_balance": 0,
                "period_debit": 0,
                "period_credit": 0,
                "closing_balance": 0,
            }
        result[row.account]["period_debit"] = row.period_debit or 0
        result[row.account]["period_credit"] = row.period_credit or 0

    # Calculate closing balance and sort
    data = sorted(result.values(), key=lambda r: (r["account_type"], r["account"]))
    for row in data:
        row["closing_balance"] = (
            row["opening_balance"] + row["period_debit"] - row["period_credit"]
        )

    return data
