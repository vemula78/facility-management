# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Shared identity resolution for the Fleet module. Ported from the PHP
prototype's api/lib.php (fleet_user, fleet_can_write, fleet_filter_visible).

Two identity mappings mirror the two the PHP prototype carried on its own
fleet_users row (actor_id / vendor_id):

* A Fleet Driver user is mapped via `User.fleet_driver` (a new custom field,
  same convention as Equipment Maintenance's `User.hem_department`) rather
  than the Contact/Dynamic-Link machinery used for Supplier — Fleet Driver is
  an app-owned doctype with no native Frappe portal-contact concept to hook
  into, so a direct Link field on User is the simpler, equally fail-closed
  choice.
* A Vendor user is resolved via equipment_maintenance.utils.supplier_for_user
  — reused as-is, not re-implemented, since Fleet's vendor identity and HEM's
  ticket-vendor identity are the same concept (a Supplier-linked Contact).
"""

import frappe

#: Roles the PHP prototype treats as never trade/identity-restricted at all —
#: Fleet Administrator is the module's own super-role, distinct from HEM's
#: OVERRIDE_ROLES (System Manager/Administrator are still an override here
#: too, same as everywhere else in this app).
OVERRIDE_ROLES = ("Administrator", "System Manager", "Fleet Administrator")

#: Roles with unrestricted staff-level visibility across Fleet doctypes —
#: mirrors fleet_filter_visible()'s implicit "any role not Vendor/Driver
#: sees everything" default in the PHP prototype.
STAFF_ROLES = (
	"Fleet Administrator",
	"Transport Manager",
	"Ambulance Coordinator",
	"Maintenance Team",
	"Finance User",
	"Management Viewer",
)


def _user(user=None):
	return user or frappe.session.user


def is_fleet_admin(user=None):
	user = _user(user)
	if user == "Administrator":
		return True
	roles = set(frappe.get_roles(user))
	return bool(roles.intersection(OVERRIDE_ROLES))


def is_fleet_staff(user=None):
	"""True for any role the PHP prototype gives blanket staff visibility to
	(everything except the identity-scoped Fleet Driver and Vendor roles)."""
	user = _user(user)
	if is_fleet_admin(user):
		return True
	roles = set(frappe.get_roles(user))
	return bool(roles.intersection(STAFF_ROLES))


def get_user_fleet_driver(user=None):
	"""The Fleet Driver record this user is identified as, or None.

	Fail-closed by design, same as get_user_department() in Equipment
	Maintenance: an unmapped Fleet Driver user sees nothing, never everything.
	"""
	user = _user(user)
	if user in ("Guest", None):
		return None
	return frappe.db.get_value("User", user, "fleet_driver") or None
