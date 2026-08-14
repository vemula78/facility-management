# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Grant the four engineering Roles baseline access to PM Schedule / PM Record.

Mirrors grant_em_contract_permissions.py exactly: without this DocPerm an
engineering role sees nothing at all and permissions.py's trade-scoping is
vacuous. The grant is deliberately broad (read/write/create/report/export) —
narrowing to the role's own trade (derived from the reference Asset's
hem_asset_class) is the job of pm_schedule_query_conditions/pm_record_query_conditions
and their has_permission counterparts in permissions.py, which further
restrict what this DocPerm allows. PM Record is submittable, so its grant
also includes submit/cancel; delete is withheld on both, same rationale as
Asset/Contract: these are records, not scrap.
"""

import frappe
from frappe.permissions import add_permission, update_permission_property

ENGINEERING_ROLES = [
	"Biomedical Engineer",
	"Civil Engineer",
	"Electrical Engineer",
	"Mechanical & Utility Engineer",
]

SCHEDULE_GRANTS = {"read": 1, "write": 1, "create": 1, "report": 1, "export": 1, "print": 1, "delete": 0}
RECORD_GRANTS = dict(SCHEDULE_GRANTS, submit=1, cancel=1)

DOCTYPE_GRANTS = {
	"PM Schedule": SCHEDULE_GRANTS,
	"PM Record": RECORD_GRANTS,
}


def execute():
	for doctype, grants in DOCTYPE_GRANTS.items():
		for role in ENGINEERING_ROLES:
			if not frappe.db.exists("Role", role):
				continue
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
				add_permission(doctype, role, 0)
			for ptype, value in grants.items():
				update_permission_property(doctype, role, 0, ptype, value)
	frappe.clear_cache()
	frappe.db.commit()
