# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""PM Record — one completed preventive-maintenance visit against a PM
Schedule. Submitting a Record rolls the linked Schedule's due_date forward by
one periodicity interval and resets its status; cancelling a Record must undo
exactly that, not leave the Schedule silently out of step with reality.

Roll-forward is measured from THIS Record's completion_date, not from the
Schedule's prior due_date — matching HEM's rule that a PM completed late is
next due one interval after when it was actually done, not one interval after
when it was originally supposed to happen (a PM done a month late does not
inherit that month's slippage forever).

Cancel restores the Schedule's due_date/status to the exact values captured
on this Record at submit time (schedule_due_date_before_roll/
schedule_status_before_roll), rather than subtracting a periodicity interval
from whatever the Schedule currently holds — an administrator could have
hand-edited the Schedule between submit and cancel, and subtracting an
interval from a since-changed value would silently produce the wrong date.

That snapshot-restore design is only correct when Records against the same
Schedule are cancelled in strict reverse-submission (LIFO) order: each
Record's snapshot is "the Schedule's state right before THIS Record's own
roll", which is only still the Schedule's live state if no later Record has
since rolled it forward again. Cancelling an older Record while a newer one
is still submitted would silently discard the newer Record's roll-forward —
found by Antigravity audit, reproduced against a two-Record sequence
(Schedule rolled by Record A, rolled again by Record B, then Record A
cancelled first: the Schedule reverted to pre-A state, erasing Record B's
still-valid completion with no error or warning). on_cancel below refuses
the cancel outright unless this Record is the most recently submitted one
still standing for its Schedule, rather than attempt a more clever revert —
the correct chained revert here (walk every still-submitted Record's
snapshot back to the true origin) is significant extra complexity for an
edge case that should simply not be allowed to happen silently.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, getdate

#: Months to advance the Schedule's due_date by, per periodicity value.
PERIODICITY_MONTHS = {
	"Monthly": 1,
	"Quarterly": 3,
	"Half-Yearly": 6,
	"Annual": 12,
}


class PMRecord(Document):
	def validate(self):
		self._denormalize_reference()

	def _denormalize_reference(self):
		# reference_doctype/reference_name live on this doctype too (read-only,
		# always re-derived here) so permission checks don't need to join
		# through PM Schedule — same reasoning as AMC CMC Warranty Contract
		# keeping its own asset link rather than deriving it elsewhere.
		if not self.pm_schedule:
			return
		schedule = frappe.db.get_value(
			"PM Schedule", self.pm_schedule, ["reference_doctype", "reference_name"], as_dict=True
		)
		if not schedule:
			frappe.throw(_("PM Schedule {0} does not exist.").format(self.pm_schedule), title=_("PM Record"))
		self.reference_doctype = schedule.reference_doctype
		self.reference_name = schedule.reference_name

	def on_submit(self):
		self._roll_schedule_forward()

	def on_cancel(self):
		self._forbid_out_of_order_cancel()
		self._revert_schedule()

	def _forbid_out_of_order_cancel(self):
		# A later Record's roll-forward is only safe to undo by THIS Record's
		# snapshot if no other submitted Record for the same Schedule was
		# SUBMITTED after this one — otherwise this Record's snapshot predates
		# that later roll and would erase it. Submission order, not maintenance
		# (completion_date) order, is what matters here.
		#
		# Uses `modified`, not `creation`, as the submission-order proxy —
		# found by Antigravity Pass 2 audit. `creation` is the draft row's
		# creation time, which can precede submission by an arbitrary amount
		# (a Record drafted Monday and submitted Wednesday, while a second
		# Record is drafted Tuesday and submitted first) and so does not track
		# submission order at all. Frappe's own submit() flow
		# (Document._submit -> save() -> set_user_and_timestamp()) sets
		# `modified` to the actual submission wall-clock time; this doctype has
		# no allow_on_submit fields and _roll_schedule_forward's own db_set
		# calls pass update_modified=False, so nothing rebumps `modified` after
		# submission — it stays a stable, accurate submission-order key here.
		newer = frappe.db.exists(
			"PM Record",
			{
				"pm_schedule": self.pm_schedule,
				"docstatus": 1,
				"name": ["!=", self.name],
				"modified": [">", self.modified],
			},
		)
		if newer:
			frappe.throw(
				_(
					"{0} cannot be cancelled while a more recently submitted PM Record "
					"({1}) still stands against the same PM Schedule — cancel that one "
					"first."
				).format(self.name, newer),
				title=_("PM Record"),
			)

	def _roll_schedule_forward(self):
		schedule = frappe.get_doc("PM Schedule", self.pm_schedule)

		# Captured on THIS record so on_cancel can restore precisely, not
		# recomputed by walking the interval backwards.
		self.db_set("schedule_due_date_before_roll", schedule.due_date, update_modified=False)
		self.db_set("schedule_status_before_roll", schedule.status, update_modified=False)

		months = PERIODICITY_MONTHS.get(schedule.periodicity)
		if not months:
			frappe.throw(
				_("PM Schedule {0} has an unrecognized periodicity {1}.").format(
					schedule.name, schedule.periodicity
				),
				title=_("PM Record"),
			)
		schedule.due_date = add_months(getdate(self.completion_date), months)
		schedule.status = "Due"
		schedule.save(ignore_permissions=True)

	def _revert_schedule(self):
		if not self.schedule_due_date_before_roll:
			# Roll-forward never ran (e.g. submit itself failed before reaching
			# on_submit) — nothing to revert.
			return
		schedule = frappe.get_doc("PM Schedule", self.pm_schedule)
		schedule.due_date = self.schedule_due_date_before_roll
		schedule.status = self.schedule_status_before_roll or "Due"
		schedule.save(ignore_permissions=True)
