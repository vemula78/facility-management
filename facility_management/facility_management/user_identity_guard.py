# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Blocks self-editing of the User fields that this app's permission scoping
keys off of: `hem_department` (Equipment Maintenance trade/department
scoping). The Fleet module's own `fleet_driver` field joins LOCKED_FIELDS
when that module is merged into this branch -- this file backports only the
hem_department half of that fix onto main ahead of Fleet.

Frappe grants every logged-in user blanket write permission on their OWN User
document -- the same mechanism that lets a user change their own password or
timezone without System Manager. That carve-out overrides DocPerm/permlevel
restrictions entirely, so `permlevel` on a field like this cannot stop a
self-edit (confirmed live on a real Frappe site while building the Fleet
module: frappe.has_permission("User", "write") returns True for any
authenticated user editing their own record, independent of role/permlevel).
This must be enforced here, in code.

Equivalent to the same defect the Fleet module's `fleet_driver` field would
have shipped with unfixed: a user holding a trade-scoped engineering role
could call frappe.get_doc("User", ...).save() on their own record and
re-point `hem_department` at a different department, seeing that
department's assets as their own via department_for_current_user().
"""

import frappe

LOCKED_FIELDS = ("hem_department",)

OVERRIDE_ROLES = ("Administrator", "System Manager")


def lock_identity_fields(doc, method=None):
	if doc.is_new():
		# Initial value on user creation (e.g. the bulk users importer, which
		# is itself gated on manage_options only) is not a self-edit.
		return

	user = frappe.session.user
	if user == "Administrator" or set(frappe.get_roles(user)).intersection(OVERRIDE_ROLES):
		return

	before = doc.get_doc_before_save()
	if not before:
		return

	for fieldname in LOCKED_FIELDS:
		if doc.get(fieldname) != before.get(fieldname):
			field_label = frappe.get_meta("User").get_label(fieldname) or fieldname
			frappe.throw(
				frappe._("You are not permitted to change your own {0}.").format(frappe._(field_label)),
				exc=frappe.PermissionError,
				title=frappe._("Not Permitted"),
			)
