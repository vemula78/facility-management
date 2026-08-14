# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Vehicle — the Fleet module's asset register. Ported from the PHP
prototype's `vehicles` collection (api/seed.json) and spec §4.1.

Field-level visibility for the Vendor/Fleet Driver roles is modeled with
Frappe DocPerm permlevels rather than a bespoke sanitize function: base
(permlevel 0) fields are the ones the PHP prototype's fleet_sanitize_visible()
allowlist shows those roles, everything else is permlevel 1, staff-only. This
is coarser than the original — the Vendor role in this port sees a few extra
base fields (fuel_type, tank_capacity, base_location, call_sign,
emergency_phone) that the PHP allowlist withheld from Vendor specifically
(it only ever showed Vendor id/assetCode/regNo/type/status/odometer). Flagged
here deliberately rather than silently ported as equivalent — see the Fleet
Foundation AGY review prompt, Section on field-level scoping.
"""

import frappe
from frappe.model.document import Document


class Vehicle(Document):
	def validate(self):
		self._enforce_odometer_forward()

	def _enforce_odometer_forward(self):
		"""Odometer readings must only move forward — ported from the PHP
		prototype's odometer validation rule (js/rules.js), enforced here
		server-side rather than only in the browser."""
		if self.is_new():
			return
		before = self.get_doc_before_save()
		if not before:
			return
		if self.odometer is not None and before.odometer is not None and self.odometer < before.odometer:
			frappe.throw(
				frappe._("Odometer reading cannot move backward (was {0}, now {1}).").format(
					before.odometer, self.odometer
				),
				title=frappe._("Vehicle"),
			)
