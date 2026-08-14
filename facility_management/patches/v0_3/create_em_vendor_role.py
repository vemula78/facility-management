# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Create the Vendor role, needed by the Breakdown/Repair Ticket slice.

Mirrors create_em_roles.py exactly, added as its own patch (not editing that
already-shipped one) since it lands with this slice, not the foundation one.
Vendor is a portal role, not a Desk role — vendor-portal users work through
ERPNext's native Contact-linked-to-Supplier pattern (see
utils.supplier_for_user()), never wp-admin-equivalent Desk access.
"""

import frappe


def execute():
	if frappe.db.exists("Role", "Vendor"):
		return
	frappe.get_doc(
		{
			"doctype": "Role",
			"role_name": "Vendor",
			"desk_access": 0,
			"is_custom": 1,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
