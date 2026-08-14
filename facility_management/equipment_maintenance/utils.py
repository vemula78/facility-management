# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Shared trade/department resolution for the Equipment Maintenance module.

Ported from the WordPress plugin's `HEM_Repository::trade_for_current_user()`,
`department_for_current_user()`, `trade_asset_classes()` and
`default_trade_for_class()`. Two rules carry over verbatim:

1. **Trade is derived from the Role, never from a user field.** One source of
   truth; a user's trade cannot drift from the role that grants them access.
2. **Class -> trade is data, not a Python dict.** It lives in the `Asset Class`
   doctype (`default_trade`), so the map can be corrected by an administrator
   without a code deploy, and so `trade -> classes` is a plain reverse lookup
   rather than a second hand-maintained dict that can disagree with the first.

Scoping is fail-closed: a trade-scoped user whose trade maps to zero asset
classes sees nothing, never everything. See `permissions.py`.
"""

import frappe

#: The four trades that back a real engineering Role. The other five trades
#: (plumbing, ac_refrigeration, it, housekeeping, other) exist for ticket
#: routing but have no dedicated role yet, exactly as in HEM v1.9.0.
ROLE_TO_TRADE = {
	"Biomedical Engineer": "biomedical",
	"Civil Engineer": "civil",
	"Electrical Engineer": "electrical",
	"Mechanical & Utility Engineer": "mechanical_utility",
}

#: Roles that are never trade-limited. Mirrors HEM's rule that `manage_options`
#: (a true WordPress Administrator) is an implicit override wherever a plugin
#: capability is checked. The raiser-exclusion carve-out where admin does NOT
#: override is specific to Capital Purchase Requisition approval steps and is
#: deliberately not implemented here.
OVERRIDE_ROLES = ("Administrator", "System Manager")


def _user(user=None):
	return user or frappe.session.user


def get_user_trade(user=None):
	"""The single engineering trade this user's roles scope them to, or None.

	Returns the `Trade` document name (its `trade_name` key, e.g. "civil").
	A user holding none of the four engineering roles returns None — that is the
	mirror-image of an unmapped department account: no trade role at all means
	no trade restriction, not zero access.
	"""
	user = _user(user)
	roles = set(frappe.get_roles(user))
	for role, trade in ROLE_TO_TRADE.items():
		if role in roles:
			return trade
	return None


def get_user_department(user=None):
	"""The Department (ERPNext HR doctype) this user is mapped to, or None.

	Fail-closed by design: an unmapped user returns None, and every caller must
	treat None as "sees nothing", never as "sees everything".
	"""
	user = _user(user)
	if user in ("Guest", None):
		return None
	return frappe.db.get_value("User", user, "hem_department") or None


def is_trade_scoped_user(user=None):
	"""True when this user's visibility must be narrowed to one trade.

	False for Administrator / System Manager even when they also hold an
	engineering role, and False for anyone holding no engineering role at all.
	"""
	user = _user(user)
	if user == "Administrator":
		return False
	if get_user_trade(user) is None:
		return False
	roles = set(frappe.get_roles(user))
	if roles.intersection(OVERRIDE_ROLES):
		return False
	return True


def asset_classes_for_trade(trade):
	"""Every Asset Class key owned by a trade — the data-driven equivalent of
	HEM's `trade_asset_classes()`. Civil legitimately owns two (furniture and
	infrastructure), which is why this is a list, not a single value."""
	if not trade:
		return []
	return frappe.get_all(
		"Asset Class",
		filters={"default_trade": trade},
		pluck="name",
		ignore_permissions=True,
	)


def default_trade_for_class(asset_class):
	"""The trade that owns an asset class — HEM's `default_trade_for_class()`,
	read from data. Returns None for an unknown class rather than guessing."""
	if not asset_class:
		return None
	return frappe.db.get_value("Asset Class", asset_class, "default_trade") or None
