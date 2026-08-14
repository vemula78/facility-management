# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Grant baseline access to Capital Purchase Requisition.

Mirrors grant_em_pm_permissions.py's structure, but the split here is by
what a role actually does in the chain rather than one shared grant:

* Department User raises requisitions (read/write/create) — no delete;
  content is locked past Draft by validate() regardless of this DocPerm.
* The eight committee/procedural roles (Director, IPC/CPC/HEC/BoT Member,
  Purchase, Stores, Finance) act on EXISTING requisitions via the
  whitelisted transition() method, never create one directly — read/write,
  no create, no delete. permissions.py's requisition_query_conditions/
  requisition_has_permission further narrow what any of these roles can
  actually reach; this DocPerm only establishes the doctype-level ceiling.
"""

import frappe
from frappe.permissions import add_permission, update_permission_property

RAISER_ROLE = "Department User"
COMMITTEE_ROLES = [
	"Director",
	"IPC Member",
	"CPC Member",
	"HEC Member",
	"BoT Member",
	"Purchase",
	"Stores",
	"Finance",
]

RAISER_GRANTS = {"read": 1, "write": 1, "create": 1, "report": 1, "export": 1, "print": 1, "delete": 0}
COMMITTEE_GRANTS = {"read": 1, "write": 1, "create": 0, "report": 1, "export": 1, "print": 1, "delete": 0}

DOCTYPE = "Capital Purchase Requisition"

ROLE_GRANTS = {RAISER_ROLE: RAISER_GRANTS}
ROLE_GRANTS.update({role: COMMITTEE_GRANTS for role in COMMITTEE_ROLES})


def execute():
	for role, grants in ROLE_GRANTS.items():
		if not frappe.db.exists("Role", role):
			continue
		if not frappe.db.exists("Custom DocPerm", {"parent": DOCTYPE, "role": role, "permlevel": 0}):
			add_permission(DOCTYPE, role, 0)
		for ptype, value in grants.items():
			update_permission_property(DOCTYPE, role, 0, ptype, value)
	frappe.clear_cache()
	frappe.db.commit()
