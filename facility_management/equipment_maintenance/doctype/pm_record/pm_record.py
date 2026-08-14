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
		self._revert_schedule()

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
