# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Trade(Document):
	pass


def prevent_delete(doc, method=None):
	"""Trades are referenced by Asset Class, tickets, PM and contracts. Deleting one
	would orphan those links; clear Is Active instead."""
	raise frappe.PermissionError(
		"Trades are never deleted — clear Is Active on the trade instead"
	)
