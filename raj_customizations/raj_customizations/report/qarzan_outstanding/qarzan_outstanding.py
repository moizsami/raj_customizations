# Copyright (c) 2026, Samtech and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.utils import get_last_day

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CURRENCY_ORDER = ["EGP", "USD", "INR"]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), build_person_rows(get_rows(filters))


def get_columns():
	return [
		{"fieldname": "full_name", "label": "Full Name", "fieldtype": "Data", "width": 260},
		{"fieldname": "amount", "label": "Amount", "fieldtype": "Currency", "options": "currency", "width": 140},
		{"fieldname": "currency", "label": "Currency", "fieldtype": "Data", "width": 90},
		{
			"fieldname": "amount_remaining",
			"label": "Amount Remaining",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{"fieldname": "return_date", "label": "Qarzan Return Date", "fieldtype": "Date", "width": 140},
	]


def get_rows(filters):
	month = filters.get("month") or MONTHS[frappe.utils.getdate().month - 1]
	year = filters.get("year") or str(frappe.utils.getdate().year)
	cutoff = get_last_day(f"{year}-{MONTHS.index(month) + 1:02d}-01")

	return frappe.db.sql(
		"""
		SELECT
			name, full_name, amount, currency, amount_remaining, return_date,
			email_address, whatsapp_number, creation
		FROM `tabQarzan System`
		WHERE COALESCE(form_submission_date, DATE(creation)) <= %(cutoff)s
			AND IFNULL(workflow_state, '') NOT IN ('Completed', 'Qarzan Rejected')
			AND IFNULL(amount_remaining, 0) != 0
		""",
		{"cutoff": cutoff},
		as_dict=True,
	)


def get_identity_keys(row):
	"""Keys that identify the same person across records with different name spellings."""
	keys = []

	email = (row.email_address or "").strip().lower()
	if email and EMAIL_RE.match(email):
		keys.append(("email", email))

	digits = re.sub(r"\D", "", row.whatsapp_number or "")
	if len(digits) >= 8:
		# last 10 digits so "+201121655889" and "01121655889" match
		keys.append(("phone", digits[-10:]))

	if not keys:
		name = re.sub(r"\s+", " ", (row.full_name or "").strip().lower())
		keys.append(("name", name or row.name))

	return keys


def build_person_rows(rows):
	# Union-find over identity keys: a record with email+phone links the two,
	# so another record carrying only the phone still lands in the same group.
	parent = {}

	def find(key):
		while parent[key] != key:
			parent[key] = parent[parent[key]]
			key = parent[key]
		return key

	def union(a, b):
		parent.setdefault(a, a)
		parent.setdefault(b, b)
		parent[find(a)] = find(b)

	record_keys = {}
	for row in rows:
		keys = get_identity_keys(row)
		record_keys[row.name] = keys
		for key in keys:
			parent.setdefault(key, key)
		for key in keys[1:]:
			union(keys[0], key)

	groups = {}
	for row in rows:
		groups.setdefault(find(record_keys[row.name][0]), []).append(row)

	# one row per person per currency; same-currency loans summed
	data = []
	for records in groups.values():
		canonical = (max(records, key=lambda r: r.creation).full_name or "").strip()
		currencies = sorted(
			{r.currency for r in records},
			key=lambda c: (CURRENCY_ORDER.index(c) if c in CURRENCY_ORDER else len(CURRENCY_ORDER), c or ""),
		)
		for currency in currencies:
			subset = [r for r in records if r.currency == currency]
			# earliest (next due) return date among this person's loans in this currency
			return_dates = [r.return_date for r in subset if r.return_date]
			data.append(
				{
					"full_name": canonical,
					"amount": sum(r.amount or 0 for r in subset),
					"currency": currency,
					"return_date": min(return_dates) if return_dates else None,
					"amount_remaining": sum(r.amount_remaining or 0 for r in subset),
				}
			)

	data.sort(key=lambda row: (row["full_name"].lower(), row["currency"] or ""))
	return data
