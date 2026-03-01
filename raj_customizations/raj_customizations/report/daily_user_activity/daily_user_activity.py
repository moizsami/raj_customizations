# Copyright (c) 2025, Raj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import today, getdate, add_days


def execute(filters=None):
	columns = get_columns()
	data, chart = get_data(filters)
	return columns, data, None, chart


def get_columns():
	"""Return columns for the report"""
	return [
		{
			"fieldname": "activity_type",
			"label": _("Activity Type"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "doctype",
			"label": _("DocType"),
			"fieldtype": "Link",
			"options": "DocType",
			"width": 200
		},
		{
			"fieldname": "count",
			"label": _("Count"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "user",
			"label": _("User"),
			"fieldtype": "Link",
			"options": "User",
			"width": 200
		}
	]


def get_data(filters):
	"""Get data for the report with dashboard summary"""
	if not filters:
		filters = {}

	# Set default date to today if not provided
	date = filters.get("date") or today()
	user_filter = filters.get("user")

	# Get created records
	created_data = get_created_records(date, user_filter)

	# Get updated records (excluding same-day creations)
	updated_data = get_updated_records(date, user_filter)

	# Get cancelled records
	cancelled_data = get_cancelled_records(date, user_filter)

	# Combine all data
	data = []

	# Add created records
	for row in created_data:
		data.append({
			"activity_type": "Created",
			"doctype": row.get("doctype"),
			"count": row.get("count"),
			"user": row.get("user") or "All Users"
		})

	# Add updated records
	for row in updated_data:
		data.append({
			"activity_type": "Updated",
			"doctype": row.get("doctype"),
			"count": row.get("count"),
			"user": row.get("user") or "All Users"
		})

	# Add cancelled records
	for row in cancelled_data:
		data.append({
			"activity_type": "Cancelled",
			"doctype": row.get("doctype"),
			"count": row.get("count"),
			"user": row.get("user") or "All Users"
		})

	# Generate chart/dashboard data
	chart = get_chart_data(created_data, updated_data, cancelled_data)

	return data, chart


def get_created_records(date, user_filter=None):
	"""Get count of records created on the given date by querying all doctypes"""
	start_date = getdate(date).strftime('%Y-%m-%d 00:00:00')
	end_date = getdate(date).strftime('%Y-%m-%d 23:59:59')

	# Get all doctypes that are standard and not single, excluding frappe app doctypes and specific doctypes
	excluded_doctypes = ['GL Entry', 'Stock Ledger Entry', 'Extra Notification Log', 'Bin', 'Payment Ledger Entry']
	doctypes = frappe.db.sql("""
		SELECT dt.name
		FROM `tabDocType` dt
		LEFT JOIN `tabModule Def` md ON dt.module = md.name
		WHERE dt.issingle = 0
		AND dt.istable = 0
		AND dt.name NOT LIKE 'old_%%'
		AND (md.app_name IS NULL OR md.app_name != 'frappe')
		AND dt.name NOT IN %(excluded_doctypes)s
	""", {"excluded_doctypes": excluded_doctypes}, as_dict=1)

	results = []

	for dt in doctypes:
		doctype = dt.get("name")

		try:
			# Skip if doctype doesn't have creation field
			columns = frappe.db.get_table_columns(doctype)
			if "creation" not in columns or "owner" not in columns:
				continue
		except Exception:
			# Table doesn't exist or other error
			continue

		try:
			# Build query based on user filter
			if user_filter:
				count = frappe.db.sql("""
					SELECT COUNT(*) as count, owner as user
					FROM `tab{doctype}`
					WHERE creation BETWEEN %(start_date)s AND %(end_date)s
					AND owner = %(user)s
					GROUP BY owner
				""".format(doctype=doctype), {
					"start_date": start_date,
					"end_date": end_date,
					"user": user_filter
				}, as_dict=1)
			else:
				count = frappe.db.sql("""
					SELECT COUNT(*) as count, 'All Users' as user
					FROM `tab{doctype}`
					WHERE creation BETWEEN %(start_date)s AND %(end_date)s
				""".format(doctype=doctype), {
					"start_date": start_date,
					"end_date": end_date
				}, as_dict=1)

			if count and count[0].get("count") > 0:
				results.append({
					"doctype": doctype,
					"count": count[0].get("count"),
					"user": count[0].get("user")
				})
		except Exception as e:
			# Skip doctypes that cause errors
			continue

	return sorted(results, key=lambda x: x.get("count"), reverse=True)


def get_updated_records(date, user_filter=None):
	"""Get count of records updated on the given date (excluding same-day creations)"""
	start_date = getdate(date).strftime('%Y-%m-%d 00:00:00')
	end_date = getdate(date).strftime('%Y-%m-%d 23:59:59')

	# Get all doctypes that are standard and not single, excluding frappe app doctypes and specific doctypes
	excluded_doctypes = ['GL Entry', 'Stock Ledger Entry', 'Extra Notification Log', 'Bin', 'Payment Ledger Entry']
	doctypes = frappe.db.sql("""
		SELECT dt.name
		FROM `tabDocType` dt
		LEFT JOIN `tabModule Def` md ON dt.module = md.name
		WHERE dt.issingle = 0
		AND dt.istable = 0
		AND dt.name NOT LIKE 'old_%%'
		AND (md.app_name IS NULL OR md.app_name != 'frappe')
		AND dt.name NOT IN %(excluded_doctypes)s
	""", {"excluded_doctypes": excluded_doctypes}, as_dict=1)

	results = []

	for dt in doctypes:
		doctype = dt.get("name")

		try:
			# Skip if doctype doesn't have required fields
			columns = frappe.db.get_table_columns(doctype)
			if "modified" not in columns or "creation" not in columns or "modified_by" not in columns:
				continue
		except Exception:
			# Table doesn't exist or other error
			continue

		try:
			# Build query based on user filter
			if user_filter:
				count = frappe.db.sql("""
					SELECT COUNT(*) as count, modified_by as user
					FROM `tab{doctype}`
					WHERE modified BETWEEN %(start_date)s AND %(end_date)s
					AND DATE(creation) != DATE(modified)
					AND modified_by = %(user)s
					GROUP BY modified_by
				""".format(doctype=doctype), {
					"start_date": start_date,
					"end_date": end_date,
					"user": user_filter
				}, as_dict=1)
			else:
				count = frappe.db.sql("""
					SELECT COUNT(*) as count, 'All Users' as user
					FROM `tab{doctype}`
					WHERE modified BETWEEN %(start_date)s AND %(end_date)s
					AND DATE(creation) != DATE(modified)
				""".format(doctype=doctype), {
					"start_date": start_date,
					"end_date": end_date
				}, as_dict=1)

			if count and count[0].get("count") > 0:
				results.append({
					"doctype": doctype,
					"count": count[0].get("count"),
					"user": count[0].get("user")
				})
		except Exception as e:
			# Skip doctypes that cause errors
			continue

	return sorted(results, key=lambda x: x.get("count"), reverse=True)


def get_cancelled_records(date, user_filter=None):
	"""Get count of records cancelled on the given date"""
	start_date = getdate(date).strftime('%Y-%m-%d 00:00:00')
	end_date = getdate(date).strftime('%Y-%m-%d 23:59:59')

	# Get all doctypes that are standard and not single, excluding frappe app doctypes and specific doctypes
	excluded_doctypes = ['GL Entry', 'Stock Ledger Entry', 'Extra Notification Log', 'Bin', 'Payment Ledger Entry']
	doctypes = frappe.db.sql("""
		SELECT dt.name
		FROM `tabDocType` dt
		LEFT JOIN `tabModule Def` md ON dt.module = md.name
		WHERE dt.issingle = 0
		AND dt.istable = 0
		AND dt.is_submittable = 1
		AND dt.name NOT LIKE 'old_%%'
		AND (md.app_name IS NULL OR md.app_name != 'frappe')
		AND dt.name NOT IN %(excluded_doctypes)s
	""", {"excluded_doctypes": excluded_doctypes}, as_dict=1)

	results = []

	for dt in doctypes:
		doctype = dt.get("name")

		try:
			# Skip if doctype doesn't have required fields
			columns = frappe.db.get_table_columns(doctype)
			if "modified" not in columns or "docstatus" not in columns or "modified_by" not in columns:
				continue
		except Exception:
			# Table doesn't exist or other error
			continue

		try:
			# Build query based on user filter
			if user_filter:
				count = frappe.db.sql("""
					SELECT COUNT(*) as count, modified_by as user
					FROM `tab{doctype}`
					WHERE modified BETWEEN %(start_date)s AND %(end_date)s
					AND docstatus = 2
					AND modified_by = %(user)s
					GROUP BY modified_by
				""".format(doctype=doctype), {
					"start_date": start_date,
					"end_date": end_date,
					"user": user_filter
				}, as_dict=1)
			else:
				count = frappe.db.sql("""
					SELECT COUNT(*) as count, 'All Users' as user
					FROM `tab{doctype}`
					WHERE modified BETWEEN %(start_date)s AND %(end_date)s
					AND docstatus = 2
				""".format(doctype=doctype), {
					"start_date": start_date,
					"end_date": end_date
				}, as_dict=1)

			if count and count[0].get("count") > 0:
				results.append({
					"doctype": doctype,
					"count": count[0].get("count"),
					"user": count[0].get("user")
				})
		except Exception as e:
			# Skip doctypes that cause errors
			continue

	return sorted(results, key=lambda x: x.get("count"), reverse=True)


def get_chart_data(created_data, updated_data, cancelled_data):
	"""Generate chart data for dashboard visualization"""

	# Aggregate by activity type
	total_created = sum([d.get("count", 0) for d in created_data])
	total_updated = sum([d.get("count", 0) for d in updated_data])
	total_cancelled = sum([d.get("count", 0) for d in cancelled_data])

	chart = {
		"data": {
			"labels": ["Created", "Updated", "Cancelled"],
			"datasets": [
				{
					"name": "Activity Count",
					"values": [total_created, total_updated, total_cancelled]
				}
			]
		},
		"type": "bar",
		"colors": ["#28a745", "#ffc107", "#dc3545"]
	}

	return chart
