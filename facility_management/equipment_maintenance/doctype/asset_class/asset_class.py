# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AssetClass(Document):
	pass


def prevent_delete(doc, method=None):
	"""Asset classes are the basis of trade scoping and are referenced by every
	Asset via hem_asset_class. Deleting one would silently widen or break scoping."""
	raise frappe.PermissionError(
		"Asset Classes are never deleted — clear Is Active on the class instead"
	)
