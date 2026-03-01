// Copyright (c) 2025, Raj and contributors
// For license information, please see license.txt

frappe.query_reports["Daily User Activity"] = {
	"filters": [
		{
			"fieldname": "date",
			"label": __("Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "user",
			"label": __("User"),
			"fieldtype": "Link",
			"options": "User"
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Make the count field clickable with proper styling
		if (column.fieldname === "count" && data && data.doctype) {
			value = `<a class="activity-count-link"
				data-doctype="${data.doctype}"
				data-activity="${data.activity_type}"
				data-user="${data.user}"
				href="javascript:void(0);"
				style="color: #2490ef; font-weight: bold; text-decoration: underline; cursor: pointer;">
				${data.count}
			</a>`;
		}

		return value;
	},

	"after_datatable_render": function(datatable) {
		// Apply row colors based on activity type using DataTable API
		const data = datatable.datamanager.data;

		data.forEach((row_data, index) => {
			let bg_color = '';

			// Determine color based on activity type
			if (row_data && row_data[0]) {  // row_data[0] is the activity_type column
				const activity_type = row_data[0].content || row_data[0];

				if (activity_type === 'Created') {
					bg_color = '#d4edda'; // Light green
				} else if (activity_type === 'Updated') {
					bg_color = '#d1ecf1'; // Light blue
				} else if (activity_type === 'Cancelled') {
					bg_color = '#f8d7da'; // Light red
				}
			}

			// Apply background color to the row
			if (bg_color) {
				const row_element = datatable.bodyRenderer.visibleRowIndices.includes(index)
					? datatable.bodyRenderer.getRowHTML(index)
					: null;

				if (row_element) {
					$(row_element).css('background-color', bg_color);
				}

				// Also update directly via DOM
				$(datatable.wrapper).find(`.dt-row[data-row-index="${index}"]`).css('background-color', bg_color);
			}
		});
	},

	"onload": function(report) {
		// Use delegated event handler on the report container
		$(document).off('click', '.activity-count-link');
		$(document).on('click', '.activity-count-link', function(e) {
			e.preventDefault();
			e.stopPropagation();

			const doctype = $(this).attr('data-doctype');
			const activity_type = $(this).attr('data-activity');
			const user = $(this).attr('data-user');

			// Get the date filter from the report
			const filters = frappe.query_report.get_filter_values();
			const date = filters.date || frappe.datetime.get_today();
			const selected_user = filters.user;

			console.log('Clicked:', doctype, activity_type, user, date);

			// Build filters for the list view
			let list_filters = {};

			if (activity_type === 'Created') {
				// Filter by creation date
				list_filters['creation'] = ['between', [date + ' 00:00:00', date + ' 23:59:59']];

				// Add user filter if specific user selected
				if (selected_user) {
					list_filters['owner'] = selected_user;
				}
			}
			else if (activity_type === 'Updated') {
				// Filter by modified date, excluding same-day creations
				// Note: Complex filters like "not between" may not work in route,
				// so we'll just filter by modified date
				list_filters['modified'] = ['between', [date + ' 00:00:00', date + ' 23:59:59']];

				// Add user filter if specific user selected
				if (selected_user) {
					list_filters['modified_by'] = selected_user;
				}
			}
			else if (activity_type === 'Cancelled') {
				// Filter by cancelled records on the date
				list_filters['modified'] = ['between', [date + ' 00:00:00', date + ' 23:59:59']];
				list_filters['docstatus'] = 2;

				// Add user filter if specific user selected
				if (selected_user) {
					list_filters['modified_by'] = selected_user;
				}
			}

			// Navigate to the list view with filters
			frappe.set_route('List', doctype, list_filters);
		});
	}
};
