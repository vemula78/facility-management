# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Fail-closed trade scoping for Equipment Maintenance.

Frappe's own **User Permissions fail OPEN**: zero User Permission rows for a
doctype means unrestricted access under the user's Role — the exact opposite of
the WordPress plugin's rule. So the scoping lives in code, and it needs BOTH
halves to be a security property:

* `permission_query_conditions` filters list/report/`frappe.get_list` queries.
* `has_permission` gates a direct single-document load
  (`frappe.get_doc` / `GET /api/resource/Asset/<name>`), which query conditions
  never touch.

Registering only the first would leave every asset readable by name to any
engineering role, which is what this module exists to prevent.

This file is the reference pattern the PM Schedule / PM Record / Ticket /
Contract / Requisition doctypes are expected to copy.
"""

import frappe

from facility_management.equipment_maintenance.utils import (
	asset_classes_for_trade,
	get_user_trade,
	is_trade_scoped_user,
)


def _allowed_classes(user):
	"""(is_scoped, classes). `is_scoped` False means no restriction applies."""
	if not is_trade_scoped_user(user):
		return False, None
	return True, asset_classes_for_trade(get_user_trade(user))


def asset_query_conditions(user=None):
	"""SQL fragment ANDed onto every Asset list query.

	Empty string = no restriction (Administrator, department users, management,
	technicians — nobody outside the four engineering roles is trade-limited at
	the doctype level).

	`1=0` = the data anomaly case: a user IS trade-scoped but their trade owns no
	Asset Class rows. That must yield nothing, never an unrestricted query.
	"""
	user = user or frappe.session.user
	scoped, classes = _allowed_classes(user)
	if not scoped:
		return ""
	if not classes:
		return "1=0"
	escaped = ", ".join(frappe.db.escape(c) for c in classes)
	# NULL hem_asset_class is excluded by the IN test — an unclassified asset is
	# deliberately invisible to a trade-scoped user rather than visible to all.
	return "(`tabAsset`.`hem_asset_class` in ({0}))".format(escaped)


def asset_has_permission(doc, ptype=None, user=None):
	"""Gate a direct single-Asset load/write for a trade-scoped user.

	Returning True here does not grant anything Frappe's own role permissions
	deny — this hook can only further restrict.
	"""
	user = user or frappe.session.user
	scoped, classes = _allowed_classes(user)
	if not scoped:
		return True
	if not classes:
		return False
	asset_class = doc.get("hem_asset_class") if hasattr(doc, "get") else None
	return bool(asset_class) and asset_class in classes
