# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class BMWBedDayRecord(Document):
	def validate(self):
		self.validate_unique_year_month()

	def validate_unique_year_month(self):
		"""Autoname is deterministic (BMW-BD-{year}-{month}), so a duplicate insert
		would otherwise surface as a raw DB primary-key IntegrityError rather than a
		clean validation message.

		Comparing names doesn't distinguish self from the pre-existing row here: on
		a genuine duplicate insert, self.name is assigned from the SAME format
		before validate() runs, so it is trivially equal to the existing row's
		name even though they are two different documents. The only reliable
		signal is self.is_new(): if this is a new document and a row with the
		expected name already exists, it is necessarily a different document (this
		one has not been inserted yet). For an update, a match only matters if it
		points to some OTHER existing row (a year/month edit colliding with a
		different record)."""
		expected_name = f"BMW-BD-{self.year}-{self.month}"
		existing = frappe.db.exists("BMW Bed-Day Record", expected_name)
		if existing and (self.is_new() or existing != self.name):
			frappe.throw(
				_("A Bed-Day Record for {0}/{1} already exists ({2}).").format(
					self.month, self.year, existing
				),
				title=_("Duplicate Period"),
			)


def prevent_delete(doc, method=None):
	"""Hard deletion is refused outright — the BMW register is append-only."""
	raise frappe.PermissionError(
		"BMW records are never deleted — void the linked handover instead"
	)
