# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Blocks self-editing of the User fields that this app's permission scoping
keys off of: `hem_department` (Equipment Maintenance trade/department scoping)
and `fleet_driver` (Fleet Driver row-level scoping).

Frappe grants every logged-in user blanket write permission on their OWN User
document -- the same mechanism that lets a user change their own password or
timezone without System Manager. That carve-out overrides DocPerm/permlevel
restrictions entirely, so `permlevel` on these fields cannot stop a self-edit;
setting permlevel:1 on `fleet_driver` was tried and confirmed NOT to block it
on a live Frappe site (frappe.has_permission("User", "write") returns True for
any authenticated user editing their own record, independent of role/
permlevel). This must be enforced here, in code.

Live-reproduced before this fix existed: a user holding only the Fleet Driver
role called frappe.get_doc("User", ...).save() on their own record and
successfully re-pointed `fleet_driver` at a different driver's record, which
would have let them see that driver's data as their own via
fleet_driver_query_conditions()/fleet_driver_has_permission().
"""

import frappe

LOCKED_FIELDS = ("hem_department", "fleet_driver")

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
