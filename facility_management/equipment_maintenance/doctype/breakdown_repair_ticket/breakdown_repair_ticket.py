# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Breakdown/Repair Ticket — shared breakdown ticket for Equipment
Maintenance's Assets today, designed to also back Fleet's Vehicle breakdown
tickets later via the same reference_doctype/reference_name dynamic link
(see pm_schedule.py for the identical pattern and its rationale). Only
"Asset" is implemented/permitted by this build.

Two independent restrictions apply to who can move a ticket's status, both
enforced here in validate(), not just hidden in the UI (mirrors HEM's
`ticket_statuses()`/`vendor_ticket_statuses()` split):

* TICKET_STATUSES is the full whitelist status may ever hold.
* VENDOR_ALLOWED_STATUSES is the narrower subset a vendor-portal user (one
  mapped to this ticket's own `vendor` Supplier via Contact, see
  utils.supplier_for_user()) may move status to. A vendor can progress a
  ticket but never close it, cancel it, or reassign the `vendor` field
  itself -- staff-only actions.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from facility_management.equipment_maintenance.utils import (
	default_trade_for_class,
	supplier_for_user,
)

#: Only "Asset" is supported by this build — see pm_schedule.ALLOWED_REFERENCE_DOCTYPES
#: for the identical rationale (Vehicle is Fleet's to add later, no schema change).
ALLOWED_REFERENCE_DOCTYPES = ("Asset",)

#: The full status lifecycle. Frappe's Select fieldtype only constrains the
#: Desk UI, not a raw API write, so validate() re-checks this defensively.
TICKET_STATUSES = ("Open", "Assigned", "In Progress", "Resolved", "Closed", "Cancelled")

#: The subset a vendor-portal user may move status to. Closed/Cancelled are
#: staff-only — a vendor finishing their work moves a ticket to Resolved,
#: never closes it themselves (HEM's rule: closing is a staff verification
#: step, not something the vendor who did the work self-certifies).
VENDOR_ALLOWED_STATUSES = ("Open", "Assigned", "In Progress", "Resolved")


class BreakdownRepairTicket(Document):
	def before_insert(self):
		# New tickets always start "Open" regardless of what a caller submits —
		# mirrors before_insert forcing a fixed initial state in every other
		# status-tracking doctype in this app (Trade/Asset Class/PM Schedule's
		# precedent doctypes; see permissions.py's reference-pattern doctypes).
		self.status = "Open"
		self.opened_at = now_datetime()

	def validate(self):
		self._validate_reference()
		self._denormalize_trade()
		self._validate_status()
		self._enforce_vendor_restrictions()
		self._stamp_lifecycle_timestamps()
		if self.is_new():
			self._snapshot_sla_response_hours()

	def _validate_reference(self):
		if self.reference_doctype not in ALLOWED_REFERENCE_DOCTYPES:
			frappe.throw(
				_("Reference Type must be one of: {0}").format(", ".join(ALLOWED_REFERENCE_DOCTYPES)),
				title=_("Breakdown/Repair Ticket"),
			)
		if not frappe.db.exists(self.reference_doctype, self.reference_name):
			frappe.throw(
				_("{0} {1} does not exist.").format(self.reference_doctype, self.reference_name),
				title=_("Breakdown/Repair Ticket"),
			)

	def _denormalize_trade(self):
		# Reporting/filtering convenience only, same caveat as PM Schedule's
		# equivalent — permissions.py never trusts this field, it re-derives
		# from the live reference on every check.
		if self.reference_doctype == "Asset":
			asset_class = frappe.db.get_value("Asset", self.reference_name, "hem_asset_class")
			self.trade = default_trade_for_class(asset_class)

	def _validate_status(self):
		if self.status not in TICKET_STATUSES:
			frappe.throw(
				_("{0} is not a valid ticket status.").format(self.status), title=_("Breakdown/Repair Ticket")
			)

	def _enforce_vendor_restrictions(self):
		if self.is_new():
			return
		supplier = supplier_for_user(frappe.session.user)
		if not supplier:
			return  # acting user is not a vendor-portal user at all -- staff, unrestricted here
		before = self.get_doc_before_save()
		if not before:
			return
		# The restriction only applies when the acting vendor is (or was) the
		# ticket's OWN vendor — this is defense-in-depth on top of permission
		# scoping, not a substitute for it: a vendor should never reach a
		# ticket that isn't theirs in the first place (see
		# permissions.ticket_has_permission), but validate() re-checks anyway,
		# matching this app's standing rule that every mutation re-verifies
		# rather than trusting the permission layer alone.
		if supplier not in (before.vendor, self.vendor):
			return
		if self.vendor != before.vendor:
			frappe.throw(
				_("A vendor cannot reassign this ticket's vendor."), title=_("Breakdown/Repair Ticket")
			)
		if self.status != before.status and self.status not in VENDOR_ALLOWED_STATUSES:
			frappe.throw(
				_("A vendor cannot set this ticket's status to {0}.").format(self.status),
				title=_("Breakdown/Repair Ticket"),
			)

	def _stamp_lifecycle_timestamps(self):
		# Each timestamp is set the first time status reaches the matching
		# state, and never overwritten once set — a ticket that bounces
		# Resolved -> In Progress -> Resolved again keeps its original
		# resolved_at, since the field records "when this first happened", not
		# "the current status's start time".
		before = self.get_doc_before_save()
		previous_status = before.status if before else None
		if self.status != "Open" and previous_status in (None, "Open") and not self.responded_at:
			self.responded_at = now_datetime()
		if self.status == "Resolved" and not self.resolved_at:
			self.resolved_at = now_datetime()
		if self.status == "Closed" and not self.closed_at:
			self.closed_at = now_datetime()

	def _snapshot_sla_response_hours(self):
		# Frozen at ticket-creation time, not a live link — a later contract
		# renewal/change must not rewrite the SLA an already-open ticket was
		# raised under. "Active" mirrors hem_amc_cmc_expiry's own definition:
		# the non-cancelled contract with the latest end_date for this asset.
		if self.reference_doctype != "Asset" or not self.reference_name:
			return
		self.sla_response_hours = frappe.db.get_value(
			"AMC CMC Warranty Contract",
			{"asset": self.reference_name, "docstatus": ["!=", 2]},
			"sla_response_hours",
			order_by="end_date desc",
		)
