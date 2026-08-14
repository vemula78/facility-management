# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Grant baseline access to Breakdown/Repair Ticket.

Mirrors grant_em_pm_permissions.py's structure. Two different grants for two
different scoping dimensions (see permissions.ticket_query_conditions):

* The four engineering Roles get the usual read/write/create/report/export/
  print, narrowed to their own trade by ticket_query_conditions/
  ticket_has_permission — same reasoning as every other grant in this app.
* Vendor gets only read/write (no create, no delete) — a vendor progresses
  tickets assigned to them, never raises or deletes one. validate()'s
  _enforce_vendor_restrictions() further narrows which status values and
  which field changes a vendor's write can actually make; this DocPerm only
  establishes that a vendor can reach the doctype at all.
"""

import frappe
from frappe.permissions import add_permission, update_permission_property

ENGINEERING_ROLES = [
	"Biomedical Engineer",
	"Civil Engineer",
	"Electrical Engineer",
	"Mechanical & Utility Engineer",
]

ENGINEERING_GRANTS = {"read": 1, "write": 1, "create": 1, "report": 1, "export": 1, "print": 1, "delete": 0}
VENDOR_GRANTS = {"read": 1, "write": 1, "create": 0, "report": 0, "export": 0, "print": 1, "delete": 0}

DOCTYPE = "Breakdown Repair Ticket"

ROLE_GRANTS = {role: ENGINEERING_GRANTS for role in ENGINEERING_ROLES}
ROLE_GRANTS["Vendor"] = VENDOR_GRANTS


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
