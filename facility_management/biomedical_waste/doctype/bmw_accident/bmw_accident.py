# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class BMWAccident(Document):
	def before_cancel(self):
		if not (self.void_reason or "").strip():
			frappe.throw(
				_("A reason is required to void an accident record. Set Void Reason before cancelling."),
				title=_("Void Reason Required"),
			)


def prevent_delete(doc, method=None):
	"""Hard deletion is refused outright — the BMW register is append-only."""
	raise frappe.PermissionError(
		"BMW records are never deleted — void the linked handover instead"
	)
