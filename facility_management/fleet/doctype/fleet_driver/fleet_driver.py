# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Fleet Driver — ported from the PHP prototype's `drivers` collection
(api/seed.json) and spec §4.2. Named "Fleet Driver" rather than "Driver" to
avoid colliding with ERPNext's own core HR "Driver" doctype, which this app
deliberately does not use (see the Fleet Foundation build decision: app-owned
doctypes, not an extension of ERPNext's built-in fleet-log feature)."""

from frappe.model.document import Document


class FleetDriver(Document):
	pass
