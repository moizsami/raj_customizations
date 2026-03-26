app_name = "raj_customizations"
app_title = "Raj Customizations"
app_publisher = "moiz@samtech-solutions.com"
app_description = "Raj Customizations"
app_email = "moiz@samtech-solutions.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "raj_customizations",
# 		"logo": "/assets/raj_customizations/logo.png",
# 		"title": "Raj Customizations",
# 		"route": "/raj_customizations",
# 		"has_permission": "raj_customizations.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------
# doc_events = {
#     "Salary Slip": {
#         "before_save": "raj_customizations.raj_customizations.weekly_absence.apply_weekly_deduction",
#         "before_save": "raj_customizations.raj_customizations.overtime_calculation.apply_weekly_deduction"
#     }
# }

#app_include_js = "/assets/custom_app/js/workflow_reject.js"

doc_events = {
    # Global validation for Read Only role - applies to ALL doctypes
    "*": {
        "validate": "raj_customizations.read_only_validation.validate_read_only_permission",
        "on_submit": "raj_customizations.read_only_validation.validate_read_only_on_submit",
        "on_cancel": "raj_customizations.read_only_validation.validate_read_only_on_cancel",
    },

    "Salary Slip": {
       # "before_save": "raj_customizations.raj_customizations.trigger_overtime_absebse.before_save_salary_slip",
       # "before_validate": "raj_customizations.public_holidays.set_public_holiday_count",
     #   "validate": "raj_customizations.last_checkin_validate.set_last_day_checkin_flag",
      #  "before_validate": "raj_customizations.last_checkin_validate.set_last_day_checkin_flag",
      #  "before_save": "raj_customizations.last_checkin_validate.set_last_day_checkin_flag",
      #  "before_insert": "raj_customizations.public_holidays.set_public_holiday_count"
    },

}


# include js, css files in header of desk.html
# app_include_css = "/assets/raj_customizations/css/raj_customizations.css"
# app_include_js = "/assets/raj_customizations/js/raj_customizations.js"
app_include_js = "/assets/raj_customizations/js/general_ledger_override_filter_and_reorder_columns.js"

# include js, css files in header of web template
# web_include_css = "/assets/raj_customizations/css/raj_customizations.css"
# web_include_js = "/assets/raj_customizations/js/raj_customizations.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "raj_customizations/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "raj_customizations/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "raj_customizations.utils.jinja_methods",
# 	"filters": "raj_customizations.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "raj_customizations.install.before_install"
# after_install = "raj_customizations.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "raj_customizations.uninstall.before_uninstall"
# after_uninstall = "raj_customizations.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "raj_customizations.utils.before_app_install"
# after_app_install = "raj_customizations.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "raj_customizations.utils.before_app_uninstall"
# after_app_uninstall = "raj_customizations.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "raj_customizations.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"raj_customizations.tasks.all"
# 	],
# 	"daily": [
# 		"raj_customizations.tasks.daily"
# 	],
# 	"hourly": [
# 		"raj_customizations.tasks.hourly"
# 	],
# 	"weekly": [
# 		"raj_customizations.tasks.weekly"
# 	],
# 	"monthly": [
# 		"raj_customizations.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "raj_customizations.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "raj_customizations.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "raj_customizations.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["raj_customizations.utils.before_request"]
# after_request = ["raj_customizations.utils.after_request"]

# Job Events
# ----------
# before_job = ["raj_customizations.utils.before_job"]
# after_job = ["raj_customizations.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"raj_customizations.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

