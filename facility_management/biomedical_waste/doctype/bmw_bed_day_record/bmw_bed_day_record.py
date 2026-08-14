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
		clean validation message. Excluding by `name` doesn't work here: a duplicate
		row necessarily has the SAME name as the existing one before it's even
		inserted, so that exclusion would wrongly exclude the very row we need to
		find. Compute the expected name instead and check for that."""
		expected_name = f"BMW-BD-{self.year}-{self.month}"
		existing = frappe.db.exists("BMW Bed-Day Record", expected_name)
		if existing and existing != self.name:
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
