# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Fail-closed row-level scoping for Fleet doctypes, following the exact
reference pattern established in equipment_maintenance/permissions.py:
`<doctype>_query_conditions` filters list views, `<doctype>_has_permission`
gates a direct single-document fetch. Both are required — Frappe's own User
Permissions fail OPEN, so every restriction here is enforced in code.

Vehicle deliberately has NO entry here — the PHP prototype gives every Fleet
role unrestricted row-level visibility on vehicles (fleet_filter_visible only
narrows *fields*, never rows, for vehicles), so Vehicle's scoping is handled
entirely by DocPerm permlevels on the doctype itself, not a hook. Fleet
Driver is the first Fleet doctype that needs row-level scoping: the PHP
prototype's `drivers` collection is visible to a Driver only as their own
record, and not reachable by a Vendor at all (fleet_filter_visible's
Vendor branch has no drivers case, so it falls through and Vendor sees
nothing — ported here as an explicit fail-closed empty condition).
"""

import frappe

from facility_management.equipment_maintenance.utils import supplier_for_user
from facility_management.fleet.utils import get_user_fleet_driver, is_fleet_staff


def fleet_driver_query_conditions(user=None):
	user = user or frappe.session.user
	if is_fleet_staff(user):
		return ""
	if supplier_for_user(user):
		# Vendor identity: the PHP prototype never exposes `drivers` to the
		# Vendor role at all — fail-closed to nothing, not "own driver".
		return "1=0"
	own_driver = get_user_fleet_driver(user)
	if not own_driver:
		# Unmapped Fleet Driver account (or any other role with no staff
		# grant and no driver mapping) — fail-closed to nothing.
		return "1=0"
	return f"""(`tabFleet Driver`.`name` = {frappe.db.escape(own_driver)})"""


def fleet_driver_has_permission(doc, ptype=None, user=None):
	# Frappe passes a bare doctype-name string when only checking whether the
	# list view itself may open, not a document instance — must return early
	# here (this was the HIGH-severity bug found on em-foundation Pass 1).
	if isinstance(doc, str):
		return True
	user = user or frappe.session.user
	if is_fleet_staff(user):
		return True
	if supplier_for_user(user):
		return False
	own_driver = get_user_fleet_driver(user)
	return bool(own_driver) and doc.name == own_driver
