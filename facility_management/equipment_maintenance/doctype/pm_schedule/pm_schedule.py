# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""PM Schedule — shared preventive-maintenance schedule for Equipment
Maintenance's Assets today, designed to also back Fleet's Vehicle PM later
via the same reference_doctype/reference_name dynamic link. Only "Asset" is
implemented and permitted by this build; ALLOWED_REFERENCE_DOCTYPES is the
single place that changes when Fleet's slice adds "Vehicle".

PM Record's on_submit/on_cancel (see pm_record.py) advance/revert this
doctype's due_date and status; nothing here mutates them directly except
validate()'s own denormalized `trade` field.
"""

import frappe
from frappe import _
from frappe.model.document import Document

#: The only reference_doctype values this build accepts, even though the
#: field itself is a generic Link to DocType (matching Frappe's own
#: reference_doctype/Dynamic Link convention, e.g. Activity Log) rather than
#: a hardcoded Select — "Vehicle" is added here, not as a schema change, once
#: Fleet's slice exists. An unrecognized value must fail validation, not
#: silently become an unscoped/unrestricted row (see permissions.py).
ALLOWED_REFERENCE_DOCTYPES = ("Asset",)


class PMSchedule(Document):
	def validate(self):
		self._validate_reference()
		self._denormalize_trade()

	def _validate_reference(self):
		if self.reference_doctype not in ALLOWED_REFERENCE_DOCTYPES:
			frappe.throw(
				_("Reference Type must be one of: {0}").format(", ".join(ALLOWED_REFERENCE_DOCTYPES)),
				title=_("PM Schedule"),
			)
		if not frappe.db.exists(self.reference_doctype, self.reference_name):
			frappe.throw(
				_("{0} {1} does not exist.").format(self.reference_doctype, self.reference_name),
				title=_("PM Schedule"),
			)

	def _denormalize_trade(self):
		# Reporting/filtering convenience only — permissions.py re-derives the
		# trade-scoping classes from the live reference on every check, it does
		# not trust this field.
		if self.reference_doctype == "Asset":
			asset_class = frappe.db.get_value("Asset", self.reference_name, "hem_asset_class")
			from facility_management.equipment_maintenance.utils import default_trade_for_class

			self.trade = default_trade_for_class(asset_class)
