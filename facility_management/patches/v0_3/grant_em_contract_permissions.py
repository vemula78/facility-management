# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Grant the four engineering Roles baseline access to AMC CMC Warranty Contract.

Mirrors grant_em_asset_permissions.py exactly: without this DocPerm an
engineering role sees nothing at all and permissions.py's trade-scoping is
vacuous. The grant is deliberately broad (read/write/create/report/export) —
narrowing to the role's own trade (derived from the linked Asset's
hem_asset_class) is the job of contract_query_conditions/contract_has_permission
in permissions.py, which further restrict what this DocPerm allows. Delete is
withheld, same rationale as Asset: contracts are a record, not scrap.
"""

import frappe
from frappe.permissions import add_permission, update_permission_property

ENGINEERING_ROLES = [
	"Biomedical Engineer",
	"Civil Engineer",
	"Electrical Engineer",
	"Mechanical & Utility Engineer",
]

GRANTS = {"read": 1, "write": 1, "create": 1, "report": 1, "export": 1, "print": 1, "delete": 0}

DOCTYPE = "AMC CMC Warranty Contract"


def execute():
	for role in ENGINEERING_ROLES:
		if not frappe.db.exists("Role", role):
			continue
		if not frappe.db.exists("Custom DocPerm", {"parent": DOCTYPE, "role": role, "permlevel": 0}):
			add_permission(DOCTYPE, role, 0)
		for ptype, value in GRANTS.items():
			update_permission_property(DOCTYPE, role, 0, ptype, value)
	frappe.clear_cache()
	frappe.db.commit()
