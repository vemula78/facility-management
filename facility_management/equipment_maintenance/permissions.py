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
Contract / Requisition doctypes are expected to copy. PM Schedule, PM
Record, Ticket and Requisition now do (below).
"""

import frappe

from facility_management.equipment_maintenance.utils import (
	asset_classes_for_user,
	get_user_department,
	is_trade_scoped_user,
	supplier_for_user,
)

#: The eight committee/procedural Roles with hospital-wide purview over every
#: Capital Purchase Requisition, regardless of which department raised it —
#: these are governance bodies, not department-scoped staff. Deliberately
#: excludes "Department User", which IS department-scoped (see
#: requisition_query_conditions).
REQUISITION_COMMITTEE_ROLES = (
	"Director",
	"IPC Member",
	"CPC Member",
	"HEC Member",
	"BoT Member",
	"Purchase",
	"Stores",
	"Finance",
)


def _allowed_classes(user):
	"""(is_scoped, classes). `is_scoped` False means no restriction applies.

	Uses the union of classes across every trade the user's roles grant — a
	user holding more than one engineering role must not lose visibility into
	all but one trade (see utils.get_user_trades()).
	"""
	if not is_trade_scoped_user(user):
		return False, None
	return True, asset_classes_for_user(user)


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
	# Frappe calls this hook for the doctype-level check too (e.g. opening the
	# Asset list in Desk, frappe.client.has_perm), passing doc="Asset" — a bare
	# string with no `hem_asset_class` to read. That check must pass so the list
	# view loads; the actual row-level restriction still happens via
	# asset_query_conditions for lists and via this same hook (with a real
	# document instance) for a single-record load.
	if isinstance(doc, str):
		return True
	asset_class = doc.get("hem_asset_class") if hasattr(doc, "get") else None
	return bool(asset_class) and asset_class in classes


def contract_query_conditions(user=None):
	"""SQL fragment ANDed onto every AMC/CMC/Warranty Contract list query.

	Contract has no asset_class field of its own — trade-scoping is derived from
	the linked Asset's hem_asset_class via a subquery against `tabAsset`, filtered
	the same way asset_query_conditions filters Asset directly.
	"""
	user = user or frappe.session.user
	scoped, classes = _allowed_classes(user)
	if not scoped:
		return ""
	if not classes:
		return "1=0"
	escaped = ", ".join(frappe.db.escape(c) for c in classes)
	return (
		"`tabAMC CMC Warranty Contract`.`asset` in "
		"(select `tabAsset`.`name` from `tabAsset` "
		"where `tabAsset`.`hem_asset_class` in ({0}))"
	).format(escaped)


def contract_has_permission(doc, ptype=None, user=None):
	"""Gate a direct single-Contract load/write for a trade-scoped user.

	Contract carries no hem_asset_class itself, so the linked Asset's class is
	loaded and run through the same class-resolution the query conditions use.
	"""
	user = user or frappe.session.user
	scoped, classes = _allowed_classes(user)
	if not scoped:
		return True
	if not classes:
		return False
	# Frappe calls this hook for the doctype-level check too (e.g. opening the
	# Contract list in Desk), passing doc="AMC CMC Warranty Contract" — a bare
	# string with no `asset` to resolve. That check must pass so the list view
	# loads; the actual row-level restriction happens via contract_query_conditions
	# for lists and via this same hook (with a real document instance) for a
	# single-record load.
	if isinstance(doc, str):
		return True
	asset = doc.get("asset") if hasattr(doc, "get") else None
	if not asset:
		return False
	asset_class = frappe.db.get_value("Asset", asset, "hem_asset_class")
	return bool(asset_class) and asset_class in classes


def _asset_class_for_reference(reference_doctype, reference_name):
	"""The hem_asset_class of a PM Schedule/Record's reference, or None.

	Only "Asset" is a supported reference_doctype in this build (see
	pm_schedule.ALLOWED_REFERENCE_DOCTYPES) — anything else, including a value
	a future Fleet slice might add before its own scoping logic lands here,
	must fail closed rather than default to unrestricted access.
	"""
	if reference_doctype != "Asset" or not reference_name:
		return None
	return frappe.db.get_value("Asset", reference_name, "hem_asset_class")


def pm_schedule_query_conditions(user=None):
	"""SQL fragment ANDed onto every PM Schedule list query.

	PM Schedule has no asset_class field of its own — trade-scoping is derived
	from the reference Asset's hem_asset_class, restricted to reference_doctype
	= 'Asset' explicitly so a future non-Asset reference_doctype value is
	excluded by this condition rather than silently unscoped.
	"""
	user = user or frappe.session.user
	scoped, classes = _allowed_classes(user)
	if not scoped:
		return ""
	if not classes:
		return "1=0"
	escaped = ", ".join(frappe.db.escape(c) for c in classes)
	return (
		"(`tabPM Schedule`.`reference_doctype` = 'Asset' and `tabPM Schedule`.`reference_name` in "
		"(select `tabAsset`.`name` from `tabAsset` "
		"where `tabAsset`.`hem_asset_class` in ({0})))"
	).format(escaped)


def pm_schedule_has_permission(doc, ptype=None, user=None):
	"""Gate a direct single-PM Schedule load/write for a trade-scoped user."""
	user = user or frappe.session.user
	scoped, classes = _allowed_classes(user)
	if not scoped:
		return True
	if not classes:
		return False
	# Frappe calls this hook for the doctype-level check too (e.g. opening the
	# PM Schedule list in Desk), passing doc="PM Schedule" — a bare string with
	# no reference to resolve. That check must pass so the list view loads; the
	# actual row-level restriction happens via pm_schedule_query_conditions for
	# lists and via this same hook (with a real document instance) for a
	# single-record load.
	if isinstance(doc, str):
		return True
	reference_doctype = doc.get("reference_doctype") if hasattr(doc, "get") else None
	reference_name = doc.get("reference_name") if hasattr(doc, "get") else None
	asset_class = _asset_class_for_reference(reference_doctype, reference_name)
	return bool(asset_class) and asset_class in classes


def ticket_query_conditions(user=None):
	"""SQL fragment ANDed onto every Breakdown/Repair Ticket list query.

	Two independent, mutually exclusive scoping paths, unlike every other
	doctype in this file which has only trade-scoping:

	* A vendor-portal user (mapped to a Supplier via Contact, see
	  utils.supplier_for_user()) sees only tickets assigned to their own
	  Supplier — trade never applies to a vendor, a vendor's assigned tickets
	  can span any trade.
	* Everyone else falls back to the same trade-scoping pattern as PM
	  Schedule/Record (reference_doctype = 'Asset' restriction, fail-closed
	  1=0 for a trade-scoped user whose trade owns no classes, unrestricted
	  for uninvolved roles).

	A user who is somehow both vendor-mapped and holds an engineering role
	(not a configuration this app's own role grants would normally produce)
	is scoped as a vendor — the narrower, portal-specific identity takes
	precedence, matching HEM's exclusive vendor-role model.
	"""
	user = user or frappe.session.user
	supplier = supplier_for_user(user)
	if supplier:
		return "(`tabBreakdown Repair Ticket`.`vendor` = {0})".format(frappe.db.escape(supplier))
	scoped, classes = _allowed_classes(user)
	if not scoped:
		return ""
	if not classes:
		return "1=0"
	escaped = ", ".join(frappe.db.escape(c) for c in classes)
	return (
		"(`tabBreakdown Repair Ticket`.`reference_doctype` = 'Asset' and "
		"`tabBreakdown Repair Ticket`.`reference_name` in "
		"(select `tabAsset`.`name` from `tabAsset` "
		"where `tabAsset`.`hem_asset_class` in ({0})))"
	).format(escaped)


def ticket_has_permission(doc, ptype=None, user=None):
	"""Gate a direct single-Ticket load/write for a vendor or a trade-scoped user."""
	user = user or frappe.session.user
	# Frappe calls this hook for the doctype-level check too (e.g. opening the
	# Ticket list in Desk), passing doc="Breakdown Repair Ticket" — a bare
	# string with no vendor/reference to resolve. That check must pass so the
	# list view loads; the actual row-level restriction happens via
	# ticket_query_conditions for lists and via this same hook (with a real
	# document instance) for a single-record load.
	if isinstance(doc, str):
		return True
	supplier = supplier_for_user(user)
	if supplier:
		vendor = doc.get("vendor") if hasattr(doc, "get") else None
		return bool(vendor) and vendor == supplier
	scoped, classes = _allowed_classes(user)
	if not scoped:
		return True
	if not classes:
		return False
	reference_doctype = doc.get("reference_doctype") if hasattr(doc, "get") else None
	reference_name = doc.get("reference_name") if hasattr(doc, "get") else None
	asset_class = _asset_class_for_reference(reference_doctype, reference_name)
	return bool(asset_class) and asset_class in classes


def pm_record_query_conditions(user=None):
	"""SQL fragment ANDed onto every PM Record list query.

	PM Record denormalizes reference_doctype/reference_name onto itself (see
	pm_record.py's validate()), so the same restriction pattern as PM Schedule
	applies directly against tabPM Record rather than via a join to PM Schedule.
	"""
	user = user or frappe.session.user
	scoped, classes = _allowed_classes(user)
	if not scoped:
		return ""
	if not classes:
		return "1=0"
	escaped = ", ".join(frappe.db.escape(c) for c in classes)
	return (
		"(`tabPM Record`.`reference_doctype` = 'Asset' and `tabPM Record`.`reference_name` in "
		"(select `tabAsset`.`name` from `tabAsset` "
		"where `tabAsset`.`hem_asset_class` in ({0})))"
	).format(escaped)


def pm_record_has_permission(doc, ptype=None, user=None):
	"""Gate a direct single-PM Record load/write for a trade-scoped user."""
	user = user or frappe.session.user
	scoped, classes = _allowed_classes(user)
	if not scoped:
		return True
	if not classes:
		return False
	# Same doctype-level string call as every other has_permission hook in
	# this file — must pass before touching doc.get(...).
	if isinstance(doc, str):
		return True
	reference_doctype = doc.get("reference_doctype") if hasattr(doc, "get") else None
	reference_name = doc.get("reference_name") if hasattr(doc, "get") else None
	asset_class = _asset_class_for_reference(reference_doctype, reference_name)
	return bool(asset_class) and asset_class in classes


def _requisition_scope(user):
	"""(unrestricted, department) for Requisition scoping.

	`unrestricted` True means no condition applies at all — Administrator or
	any of the eight committee/procedural Roles, which have hospital-wide
	purview by design (see REQUISITION_COMMITTEE_ROLES). Otherwise
	`department` is this user's own hem_department (possibly None), and the
	caller must ALSO allow rows where raised_by = this user regardless of
	department — a user who raised a requisition can always see their own,
	even with no department mapped at all, or from a department other than
	the one they're currently mapped to.
	"""
	if _is_admin_for_requisitions(user):
		return True, None
	roles = set(frappe.get_roles(user))
	if roles.intersection(REQUISITION_COMMITTEE_ROLES):
		return True, None
	return False, get_user_department(user)


def _is_admin_for_requisitions(user):
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def requisition_query_conditions(user=None):
	"""SQL fragment ANDed onto every Capital Purchase Requisition list query.

	Unlike every other doctype in this file, scoping here is department- and
	role-based, not trade-based: a Requisition has no Asset Class of its own
	and its raising department can be entirely unrelated to any engineering
	trade. Committee/procedural roles (Director, IPC/CPC/HEC/BoT Member,
	Purchase, Stores, Finance) see everything — they are hospital-wide
	governance bodies, not department-scoped staff. Everyone else sees their
	own department's requisitions AND anything they personally raised, even
	if raised before/after a department reassignment or with no department
	mapped at all.
	"""
	user = user or frappe.session.user
	unrestricted, department = _requisition_scope(user)
	if unrestricted:
		return ""
	escaped_user = frappe.db.escape(user)
	if not department:
		return "(`tabCapital Purchase Requisition`.`raised_by` = {0})".format(escaped_user)
	escaped_dept = frappe.db.escape(department)
	return (
		"((`tabCapital Purchase Requisition`.`department` = {0}) or "
		"(`tabCapital Purchase Requisition`.`raised_by` = {1}))"
	).format(escaped_dept, escaped_user)


def requisition_has_permission(doc, ptype=None, user=None):
	"""Gate a direct single-Requisition load/write for a department-scoped user."""
	user = user or frappe.session.user
	# Doctype-level string call, same guard as every other has_permission hook
	# in this file — must pass before touching doc.get(...).
	if isinstance(doc, str):
		return True
	unrestricted, department = _requisition_scope(user)
	if unrestricted:
		return True
	raised_by = doc.get("raised_by") if hasattr(doc, "get") else None
	if raised_by == user:
		return True
	doc_department = doc.get("department") if hasattr(doc, "get") else None
	return bool(department) and bool(doc_department) and department == doc_department
