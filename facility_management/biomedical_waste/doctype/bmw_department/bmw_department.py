# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BMWDepartment(Document):
	pass


def prevent_delete(doc, method=None):
	"""Hard deletion is refused outright — deleting a department would orphan the
	`department` link on every historical bag it appears on. Deactivate it instead."""
	raise frappe.PermissionError(
		"BMW records are never deleted — clear Is Active on the department instead"
	)
