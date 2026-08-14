# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Grant the four engineering Roles baseline access to Asset, Trade and Asset Class.

Without a DocPerm on Asset, an engineering role sees nothing at all and the
trade-scoping layer is vacuous. The role permission is deliberately broad
(read/write/create/report/export) — narrowing to the role's own trade is the job
of `permissions.py`, which further restricts what these DocPerms allow. Delete is
withheld: assets are retired, not removed.

Trade and Asset Class are read-only to these roles (their doctype JSON already
grants `All` read); this patch only adds the Asset grant.
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


def execute():
	for role in ENGINEERING_ROLES:
		if not frappe.db.exists("Role", role):
			continue
		if not frappe.db.exists("Custom DocPerm", {"parent": "Asset", "role": role, "permlevel": 0}):
			add_permission("Asset", role, 0)
		for ptype, value in GRANTS.items():
			update_permission_property("Asset", role, 0, ptype, value)
	frappe.clear_cache()
	frappe.db.commit()
