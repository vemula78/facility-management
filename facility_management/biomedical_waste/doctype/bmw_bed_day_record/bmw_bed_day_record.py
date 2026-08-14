# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class BMWBedDayRecord(Document):
	def validate(self):
		self.validate_unique_year_month()

	def validate_unique_year_month(self):
		existing = frappe.db.get_value(
			"BMW Bed-Day Record",
			{"year": self.year, "month": self.month, "name": ["!=", self.name]},
			"name",
		)
		if existing:
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
