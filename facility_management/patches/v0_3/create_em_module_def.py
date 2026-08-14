# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Create the 'Equipment Maintenance' Module Def before any doctype syncs.

Runs in [pre_model_sync] deliberately. Without an existing Module Def, Frappe
resolves a new DocType's controller module against `frappe.core` and migrate
dies with `No module named 'frappe.core.doctype.trade'` before the Module Def
would otherwise have been created. Idempotent.
"""

import frappe


def execute():
	if frappe.db.exists("Module Def", "Equipment Maintenance"):
		return
	frappe.get_doc(
		{
			"doctype": "Module Def",
			"module_name": "Equipment Maintenance",
			"app_name": "facility_management",
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
