# Copyright (c) 2025, Raj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import today, getdate


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
			"user": row.get("owner") if user_filter else "All Users"
		})

	# Add updated records
	for row in updated_data:
		data.append({
			"activity_type": "Updated",
			"doctype": row.get("doctype"),
			"count": row.get("count"),
			"user": row.get("modified_by") if user_filter else "All Users"
		})

	# Add cancelled records
	for row in cancelled_data:
		data.append({
			"activity_type": "Cancelled",
			"doctype": row.get("doctype"),
			"count": row.get("count"),
			"user": row.get("modified_by") if user_filter else "All Users"
		})

	# Generate chart/dashboard data
	chart = get_chart_data(created_data, updated_data, cancelled_data)

	return data, chart


def get_created_records(date, user_filter=None):
	"""Get count of records created on the given date"""
	conditions = "DATE(creation) = %(date)s"
	params = {"date": getdate(date)}

	if user_filter:
		conditions += " AND owner = %(user)s"
		params["user"] = user_filter

	query = f"""
		SELECT
			doctype,
			owner,
			COUNT(*) as count
		FROM
			`tabVersion`
		WHERE
			{conditions}
			AND docstatus != 2
			AND data LIKE '%"changed":%"creation"%'
		GROUP BY
			doctype, owner
		ORDER BY
			count DESC
	"""

	# Alternative approach using Version table
	# Get all doctypes that have records created today
	result = frappe.db.sql("""
		SELECT
			ref_doctype as doctype,
			owner,
			COUNT(DISTINCT docname) as count
		FROM
			`tabVersion`
		WHERE
			DATE(creation) = %(date)s
			{user_condition}
			AND data LIKE '%"changed"%'
			AND (data LIKE '%"added":%' OR creation = modified)
		GROUP BY
			ref_doctype, owner
		ORDER BY
			count DESC
	""".format(
		user_condition="AND owner = %(user)s" if user_filter else ""
	), params, as_dict=1)

	return result


def get_updated_records(date, user_filter=None):
	"""Get count of records updated on the given date (excluding same-day creations)"""
	conditions = "DATE(v.modified) = %(date)s"
	params = {"date": getdate(date)}

	if user_filter:
		conditions += " AND v.modified_by = %(user)s"
		params["user"] = user_filter

	# Get updates where creation date != update date
	result = frappe.db.sql(f"""
		SELECT
			v.ref_doctype as doctype,
			v.modified_by,
			COUNT(DISTINCT v.docname) as count
		FROM
			`tabVersion` v
		WHERE
			{conditions}
			AND DATE(v.creation) != %(date)s
			AND v.data LIKE '%"changed"%'
			AND v.data NOT LIKE '%"added":%'
		GROUP BY
			v.ref_doctype, v.modified_by
		ORDER BY
			count DESC
	""", params, as_dict=1)

	return result


def get_cancelled_records(date, user_filter=None):
	"""Get count of records cancelled on the given date"""
	conditions = "DATE(v.modified) = %(date)s"
	params = {"date": getdate(date)}

	if user_filter:
		conditions += " AND v.modified_by = %(user)s"
		params["user"] = user_filter

	result = frappe.db.sql(f"""
		SELECT
			v.ref_doctype as doctype,
			v.modified_by,
			COUNT(DISTINCT v.docname) as count
		FROM
			`tabVersion` v
		WHERE
			{conditions}
			AND v.data LIKE '%"docstatus":%2%'
		GROUP BY
			v.ref_doctype, v.modified_by
		ORDER BY
			count DESC
	""", params, as_dict=1)

	return result


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
