# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Create the seven Fleet-specific Roles, ported from the PHP prototype's
FLEET_ROLES constant (api/lib.php) minus "Vendor" — that role already exists
(created by Equipment Maintenance's create_em_vendor_role patch for the
Breakdown/Repair Ticket vendor portal) and is reused as-is here rather than
duplicated. One vendor identity across the whole app, not two: a Supplier
contact holding the "Vendor" role reaches both their HEM tickets and their
Fleet breakdowns/PM records through the same frappe.get_roles() check.

"Fleet Administrator" is deliberately its own role, not reused from
Equipment Maintenance's admin pattern — the PHP prototype treats it as a
Fleet-scoped super-role, not the same concept as manage_options/System
Manager, and fleet.utils.OVERRIDE_ROLES reflects that (see utils.py).
"""

import frappe

ROLES = [
	"Fleet Administrator",
	"Transport Manager",
	"Ambulance Coordinator",
	"Fleet Driver",
	"Maintenance Team",
	"Finance User",
	"Management Viewer",
]


def execute():
	for role_name in ROLES:
		if frappe.db.exists("Role", role_name):
			continue
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
				"is_custom": 1,
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
