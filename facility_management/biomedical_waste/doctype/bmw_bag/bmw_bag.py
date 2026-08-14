# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, now_datetime

MIN_WEIGHT_KG = 0.01
MAX_WEIGHT_KG = 500.00
MAX_BACKDATE_DAYS = 60


class BMWBag(Document):
	def validate(self):
		self.validate_cytotoxic()
		self.validate_weight()
		self.validate_generated_at_window()
		self.validate_status_not_hand_edited()

	def validate_cytotoxic(self):
		if self.is_cytotoxic and self.category != "Yellow":
			frappe.throw(
				_("Cytotoxic waste can only be recorded against a Yellow category bag."),
				title=_("Invalid Category"),
			)

	def validate_weight(self):
		weight = frappe.utils.flt(self.weight_kg, 2)
		if weight < MIN_WEIGHT_KG or weight > MAX_WEIGHT_KG:
			frappe.throw(
				_("Weight must be between {0} and {1} kg (got {2}).").format(
					MIN_WEIGHT_KG, MAX_WEIGHT_KG, weight
				),
				title=_("Invalid Weight"),
			)
		self.weight_kg = weight

	def validate_generated_at_window(self):
		"""Enforce the generation-date window only when generated_at is actually being set or changed.

		A bag whose handover was voided flips back to Open with generated_at untouched; it must
		remain editable no matter how old it is. So the 60-day backdating limit applies only on
		insert, or when the user changes generated_at on an existing bag.
		"""
		if not self.is_new():
			previous = self.get_doc_before_save()
			if previous and get_datetime(previous.generated_at) == get_datetime(self.generated_at):
				return

		generated_at = get_datetime(self.generated_at)
		now = now_datetime()

		if generated_at > now:
			frappe.throw(_("Generated At cannot be in the future."), title=_("Invalid Date"))

		if generated_at < get_datetime(add_days(now, -MAX_BACKDATE_DAYS)):
			frappe.throw(
				_("Generated At cannot be more than {0} days in the past.").format(MAX_BACKDATE_DAYS),
				title=_("Invalid Date"),
			)

	def validate_status_not_hand_edited(self):
		"""status is owned by BMW Handover submit/cancel, which write it via frappe.db.set_value
		and therefore never pass through this controller. Any status change that does reach
		validate() is a direct user edit, and is refused — with exactly one exception, the
		void path below (the port of the original plugin's void_bag()).

		Permitted direct transition: Open -> Void, and only when
		  * void_reason holds real, non-whitespace content saved on the same edit, and
		  * the bag is not claimed by a handover (self.handover is empty). A bag already
		    on a handover must be withdrawn by cancelling that handover, not voided here.
		Everything else (Open -> Handed Over by hand, Void -> anything, Handed Over ->
		anything) stays blocked exactly as before."""
		if self.is_new():
			if self.status and self.status != "Open":
				frappe.throw(
					_("A new bag must be created with status Open."), title=_("Invalid Status")
				)
			return

		previous = self.get_doc_before_save()
		if previous and previous.status != self.status:
			if previous.status == "Open" and self.status == "Void":
				self.validate_void()
				return
			frappe.throw(
				_("Bag status is set by the handover workflow and cannot be edited directly."),
				title=_("Invalid Status"),
			)

	def validate_void(self):
		"""Guard rails for the single permitted direct status transition, Open -> Void."""
		if not (self.void_reason or "").strip():
			frappe.throw(
				_("A reason is required to void a bag. Set Void Reason before saving."),
				title=_("Void Reason Required"),
			)

		if self.handover:
			frappe.throw(
				_(
					"Bag {0} is part of handover {1} and cannot be voided directly. "
					"Cancel the handover instead."
				).format(self.name, self.handover),
				title=_("Bag Claimed by Handover"),
			)


def prevent_delete(doc, method=None):
	"""Hard deletion is refused outright — the BMW register is append-only."""
	raise frappe.PermissionError(
		"BMW records are never deleted — void the linked handover instead"
	)
