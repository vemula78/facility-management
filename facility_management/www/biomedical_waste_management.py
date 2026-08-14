# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Public, no-login BMW disclosure page.

Security boundary (do not weaken): exposes only administrator-maintained
BMW Settings fields and aggregate, non-void category totals grouped by
month/year. Never exposes individual bag rows, department names, handover
manifest numbers, receiver names, or anything from BMW Accident. Category
totals are filtered on BMW Bag's own `status != 'Void'`, not on the linked
handover's status: the aggregate excludes only bags explicitly voided, and
counts everything else.
"""

import frappe

no_cache = 1
no_sitemap = 0

CATEGORIES = ["Yellow", "Red", "White", "Blue"]


def get_context(context):
	current_year = frappe.utils.now_datetime().year
	year = frappe.utils.cint(frappe.form_dict.get("year")) or current_year
	if year < 2016 or year > current_year:
		year = current_year

	settings = frappe.get_single("BMW Settings")

	context.settings = {
		"facility_name": settings.facility_name,
		"facility_address": settings.facility_address,
		"contact_phone": settings.contact_phone,
		"contact_email": settings.contact_email,
		"bed_count": settings.bed_count,
		"kspcb_auth_no": settings.kspcb_auth_no,
		"kspcb_auth_valid_until": settings.kspcb_auth_valid_until,
		"water_consent_no": settings.water_consent_no,
		"water_consent_valid_until": settings.water_consent_valid_until,
		"air_consent_no": settings.air_consent_no,
		"air_consent_valid_until": settings.air_consent_valid_until,
		"disposal_mode": settings.disposal_mode,
		"cbwtf_name": settings.cbwtf_name,
		"cbwtf_address": settings.cbwtf_address,
		"captive_treated_kg_day": settings.captive_treated_kg_day,
		"captive_equipment_details": settings.captive_equipment_details,
		"captive_equipment_count_capacity": settings.captive_equipment_count_capacity,
		"captive_operating_parameters": settings.captive_operating_parameters,
		"training_year": settings.training_year,
		"training_count": settings.training_count,
		"bmw_workers_total": settings.bmw_workers_total,
		"bmw_workers_immunized": settings.bmw_workers_immunized,
	}

	context.year = year
	context.current_year = current_year
	context.year_options = list(range(current_year, max(2016, current_year - 10) - 1, -1))
	context.months = _monthly_category_totals(year)
	context.annual_totals = {
		cat: round(sum(m[cat] for m in context.months), 2) for cat in CATEGORIES
	}
	context.annual_total = round(sum(context.annual_totals.values()), 2)

	current_month_rows = _monthly_category_totals(current_year)
	this_month = frappe.utils.now_datetime().month
	month_kg = sum(current_month_rows[this_month - 1][cat] for cat in CATEGORIES)
	days_elapsed = max(1, frappe.utils.now_datetime().day)
	context.daily_average = round(month_kg / days_elapsed, 2)
	context.generated_on = frappe.utils.now()

	return context


def _monthly_category_totals(year):
	"""Aggregate, non-void category totals for the given year, grouped by month.

	Filters on BMW Bag.status directly (never on BMW Handover.status): the only
	bags excluded are those with status == 'Void'. Bags that are 'Open' —
	including ones reopened by a cancelled handover — and bags that are
	'Handed Over' are BOTH counted, because waste is counted at the point of
	generation, not at disposal. This matches the original plugin's behaviour.
	A bag recorded in error is withdrawn from these totals by voiding the bag
	itself (Open -> Void with a void reason), not by cancelling its handover.
	"""
	rows = frappe.db.sql(
		"""
		SELECT MONTH(generated_at) AS month, category, SUM(weight_kg) AS total_kg
		FROM `tabBMW Bag`
		WHERE YEAR(generated_at) = %(year)s
		  AND status != 'Void'
		GROUP BY MONTH(generated_at), category
		""",
		{"year": year},
		as_dict=True,
	)

	by_month = {m: {cat: 0.0 for cat in CATEGORIES} for m in range(1, 13)}
	for row in rows:
		if row.category in CATEGORIES:
			by_month[row.month][row.category] = round(frappe.utils.flt(row.total_kg, 2), 2)

	return [by_month[m] for m in range(1, 13)]
