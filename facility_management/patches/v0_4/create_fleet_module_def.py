# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Create the 'Fleet' Module Def before any doctype syncs.

Same reason as Equipment Maintenance's create_em_module_def: without an
existing Module Def, Frappe resolves a new DocType's controller module
against `frappe.core` and migrate dies before the Module Def would otherwise
have been created. Idempotent. Runs in [pre_model_sync].
"""

import frappe


def execute():
	if frappe.db.exists("Module Def", "Fleet"):
		return
	frappe.get_doc(
		{
			"doctype": "Module Def",
			"module_name": "Fleet",
			"app_name": "facility_management",
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
