# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Seed BMW Settings with obviously-fake placeholder values.

Deliberate scope decision (see task spec): every facility-specific and
statutory value here is a placeholder, including the authorisation number and
validity date, because the real KSPCB authorisation has lapsed and the
renewed value is not yet available. Never seed a plausible-looking real
value — that is the kind of thing that gets copied into a real filing by
mistake. Idempotent: only fills a field if it is still empty, so a value an
administrator has already entered is never overwritten.
"""

import frappe

PLACEHOLDERS = {
	"facility_name": "UPDATE ME — facility name not yet confirmed",
	"facility_address": "UPDATE ME — facility address not yet confirmed",
	"contact_phone": "UPDATE ME",
	"contact_email": "update-me@example.invalid",
	"bed_count": 0,
	"kspcb_auth_no": "UPDATE ME — PLACEHOLDER, NOT A REAL AUTHORISATION NUMBER",
	"kspcb_auth_valid_until": None,
	"water_consent_no": "UPDATE ME — PLACEHOLDER",
	"water_consent_valid_until": None,
	"air_consent_no": "UPDATE ME — PLACEHOLDER",
	"air_consent_valid_until": None,
	"auth_capacity_yellow_kg_day": 0,
	"auth_capacity_red_kg_day": 0,
	"auth_capacity_white_kg_day": 0,
	"auth_capacity_blue_kg_day": 0,
	"disposal_mode": "CBWTF",
	"cbwtf_name": "UPDATE ME — CBWTF name not yet confirmed",
	"cbwtf_address": "UPDATE ME — CBWTF address not yet confirmed",
	"cbwtf_monthly_cap_kg": 0,
	"cbwtf_excess_rate_per_kg": 0,
	"storage_provision": "UPDATE ME — storage/treatment/transport provision not yet described",
	"committee_exists": 0,
	"committee_meetings_count": 0,
	"committee_minutes_note": "",
	"training_year": 0,
	"training_count": 0,
	"personnel_trained": 0,
	"personnel_trained_induction": 0,
	"personnel_not_trained": 0,
	"training_manual_available": 0,
	"bmw_workers_total": 0,
	"bmw_workers_immunized": 0,
}


def execute():
	settings = frappe.get_single("BMW Settings")
	changed = False
	for fieldname, value in PLACEHOLDERS.items():
		if not settings.get(fieldname):
			settings.set(fieldname, value)
			changed = True

	# The validity-date fields carry the "needs confirming" caveat in their
	# field description (set in the doctype JSON), not in a fake date value —
	# a plausible-looking date is exactly what must not be seeded here.
	if changed:
		settings.save(ignore_permissions=True)
		frappe.db.commit()
