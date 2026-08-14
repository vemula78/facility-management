# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

MAX_BAGS_PER_HANDOVER = 500


class BMWHandover(Document):
	def validate(self):
		self.validate_bag_count()
		self.validate_no_duplicate_bags()
		self.calculate_totals()

	def validate_bag_count(self):
		if not self.bags:
			frappe.throw(_("At least one bag must be selected for handover."), title=_("No Bags"))

		if len(self.bags) > MAX_BAGS_PER_HANDOVER:
			frappe.throw(
				_("A maximum of {0} bags may be included in a single handover (got {1}).").format(
					MAX_BAGS_PER_HANDOVER, len(self.bags)
				),
				title=_("Too Many Bags"),
			)

	def validate_no_duplicate_bags(self):
		seen = set()
		for row in self.bags:
			if row.bag in seen:
				frappe.throw(
					_("Bag {0} appears more than once in this handover.").format(row.bag),
					title=_("Duplicate Bag"),
				)
			seen.add(row.bag)

	def calculate_totals(self):
		"""Compute the five weight totals server-side from the child rows.

		IMPORTANT: cytotoxic_kg is a SUBSET of yellow_kg, not a sixth disjoint stream.
		yellow_kg  = sum of weight over ALL Yellow rows (cytotoxic or not)
		cytotoxic_kg = sum of weight over Yellow rows where is_cytotoxic is true
		Consequently the total consignment weight is yellow + red + white + blue ONLY.
		Any downstream report or dashboard that adds all five columns together will
		double-count the cytotoxic weight.
		"""
		totals = {"Yellow": 0.0, "Red": 0.0, "White": 0.0, "Blue": 0.0}
		cytotoxic = 0.0

		for row in self.bags:
			weight = flt(row.weight_kg, 2)
			if row.category in totals:
				totals[row.category] += weight
			if row.category == "Yellow" and row.is_cytotoxic:
				cytotoxic += weight

		self.yellow_kg = flt(totals["Yellow"], 2)
		self.red_kg = flt(totals["Red"], 2)
		self.white_kg = flt(totals["White"], 2)
		self.blue_kg = flt(totals["Blue"], 2)
		self.cytotoxic_kg = flt(cytotoxic, 2)

	def _lock_bags(self):
		"""Lock the claimed bag rows FOR UPDATE inside the request's existing transaction,
		so a concurrent handover cannot claim the same bags. Frappe already runs each request
		in a transaction and rolls it back on an uncaught exception; no extra wrapper here."""
		bag_names = [row.bag for row in self.bags]
		return frappe.db.sql(
			"SELECT name, status FROM `tabBMW Bag` WHERE name IN %(bags)s FOR UPDATE",
			{"bags": bag_names},
			as_dict=True,
		)

	def before_submit(self):
		locked = self._lock_bags()

		found = {row.name for row in locked}
		missing = [row.bag for row in self.bags if row.bag not in found]
		if missing:
			frappe.throw(
				_("One or more selected bags could not be found: {0}").format(", ".join(missing)),
				title=_("Bag Not Found"),
			)

		not_open = [row.name for row in locked if row.status != "Open"]
		if not_open:
			frappe.throw(
				_("The following bags are no longer open and cannot be handed over: {0}").format(
					", ".join(sorted(not_open))
				),
				title=_("Bag Not Open"),
				exc=frappe.ValidationError,
			)

		# Deliberately frappe.db.set_value, not get_doc().save(): re-running full bag
		# validation per bag would defeat the point of holding the row lock cleanly.
		for row in self.bags:
			frappe.db.set_value(
				"BMW Bag", row.bag, {"status": "Handed Over", "handover": self.name}
			)

	def before_cancel(self):
		if not (self.void_reason or "").strip():
			frappe.throw(
				_("A reason is required to void a handover. Set Void Reason before cancelling."),
				title=_("Void Reason Required"),
			)

	def on_cancel(self):
		self._lock_bags()

		for row in self.bags:
			frappe.db.set_value("BMW Bag", row.bag, {"status": "Open", "handover": None})


def prevent_delete(doc, method=None):
	"""Hard deletion is refused outright — the BMW register is append-only. A cancelled
	handover retains its void reason, manifest number and receiver acknowledgement."""
	raise frappe.PermissionError(
		"BMW records are never deleted — cancel the handover with a void reason instead"
	)
