# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Create the four trade-scoped engineering Roles.

A patch rather than a fixture because this app has no fixtures hook and BMW set
no precedent for one; a patch is idempotent, ordered relative to the doctype
sync, and visible in `bench migrate` output. Roles are desk roles (not portal
roles) — these users work in the Desk, same as HEM's engineering roles worked in
wp-admin/the staff portal.
"""

import frappe

ROLES = [
	"Biomedical Engineer",
	"Civil Engineer",
	"Electrical Engineer",
	"Mechanical & Utility Engineer",
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
