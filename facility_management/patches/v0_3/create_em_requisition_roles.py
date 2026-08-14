# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Create the nine Roles the Capital Purchase Requisition chain needs.

Mirrors create_em_roles.py/create_em_vendor_role.py exactly. Enumerated
explicitly per the design plan's own instruction ("enumerate these
explicitly at build time, don't improvise"): Director, IPC Member,
CPC Member, HEC Member, BoT Member, Purchase, Stores, Finance, and
Department User (the raising department's own role — every other role here
is a committee/procedural body with hospital-wide purview, this one is the
department-scoped exception, see permissions.requisition_query_conditions).
All nine are Desk roles — unlike Vendor, nobody in this chain is an external
portal user.
"""

import frappe

ROLES = [
	"Director",
	"IPC Member",
	"CPC Member",
	"HEC Member",
	"BoT Member",
	"Purchase",
	"Stores",
	"Finance",
	"Department User",
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
