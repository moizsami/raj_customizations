"""
Read Only Role Validation
Prevents users with 'Read Only' role from making any document changes.
Optimized to only check when necessary to avoid performance impact.
"""

import frappe
from frappe import _

# Cache key for storing role check results per request
_ROLE_CACHE_KEY = "_read_only_role_check"


def has_read_only_role():
	"""
	Check if current user has 'Read Only' role.
	Uses request-level caching to avoid multiple DB queries.

	Returns:
		bool: True if user has Read Only role, False otherwise
	"""
	# Check if result is already cached in current request
	if hasattr(frappe.local, _ROLE_CACHE_KEY):
		return getattr(frappe.local, _ROLE_CACHE_KEY)

	# Perform the actual role check
	has_role = "Read Only" in frappe.get_roles()

	# Cache the result for this request
	setattr(frappe.local, _ROLE_CACHE_KEY, has_role)

	return has_role


def validate_read_only_permission(doc, method=None):
	"""
	Validate that users with 'Read Only' role cannot modify documents.

	This function is called on the 'validate' event for all doctypes.
	It uses early exit pattern to minimize performance impact:
	- Returns immediately for users without Read Only role
	- Returns immediately for documents being loaded (not modified)
	- Skips system/session doctypes to allow login and system operations

	Args:
		doc: The document being validated
		method: The event method name (validate, before_save, etc.)
	"""
	# Early exit: Skip for system users (Administrator, Guest)
	if frappe.session.user in ("Administrator", "Guest"):
		return

	# Early exit: Skip system and session-related doctypes
	# These are needed for login, navigation, and system operations
	ALLOWED_DOCTYPES = (
		"Session",
		"Activity Log",
		"View Log",
		"Access Log",
		"Error Log",
		"Route History",
		"Comment",
		"Version",
		"Communication",
		"Email Queue",
		"Notification Log",
		"Prepared Report",
		"Document Follow",
		"User Settings",
		"DefaultValue",
		"User Permission",
		"DocShare",
		"File",
		"OAuth Bearer Token",
		"Token Cache"
	)

	if doc.doctype in ALLOWED_DOCTYPES:
		return

	# Early exit: Skip if user doesn't have Read Only role
	# This is the key optimization - most users will exit here
	if not has_read_only_role():
		return

	# Early exit: Skip if document is being loaded (not modified)
	# New documents will have is_new() = True
	# Modified documents will have has_value_changed() or is being submitted/cancelled
	if not doc.is_new() and not doc.has_value_changed() and doc.docstatus == 0:
		return

	# Block any modification attempts
	action = _get_action_description(doc)

	frappe.throw(
		_("You have a 'Read Only' role and cannot {0} documents.").format(action),
		frappe.PermissionError,
		title=_("Action Not Permitted")
	)


def _get_action_description(doc):
	"""
	Get a human-readable description of what action is being attempted.

	Args:
		doc: The document being modified

	Returns:
		str: Action description (create, update, submit, cancel, amend)
	"""
	if doc.is_new():
		return _("create")
	elif doc.docstatus == 0:
		return _("update")
	elif doc.docstatus == 1:
		return _("submit")
	elif doc.docstatus == 2:
		return _("cancel")
	else:
		return _("modify")


def validate_read_only_on_submit(doc, method=None):
	"""
	Specifically blocks submit actions for Read Only users.
	This runs on 'on_submit' event as an additional safeguard.

	Args:
		doc: The document being submitted
		method: The event method name
	"""
	# Early exit: Skip for system users
	if frappe.session.user in ("Administrator", "Guest"):
		return

	# Early exit: Skip if user doesn't have Read Only role
	if not has_read_only_role():
		return

	frappe.throw(
		_("You have a 'Read Only' role and cannot submit documents."),
		frappe.PermissionError,
		title=_("Submit Not Permitted")
	)


def validate_read_only_on_cancel(doc, method=None):
	"""
	Specifically blocks cancel actions for Read Only users.
	This runs on 'on_cancel' event as an additional safeguard.

	Args:
		doc: The document being cancelled
		method: The event method name
	"""
	# Early exit: Skip for system users
	if frappe.session.user in ("Administrator", "Guest"):
		return

	# Early exit: Skip if user doesn't have Read Only role
	if not has_read_only_role():
		return

	frappe.throw(
		_("You have a 'Read Only' role and cannot cancel documents."),
		frappe.PermissionError,
		title=_("Cancel Not Permitted")
	)