# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Seed the nine Trades and six Asset Classes.

Both maps are ported verbatim from `HEM_Repository` (v1.9.0):

* `trades()` — all nine ticket-routing trades. `carpentry` was retired there in
  1.9.0 and folded into `civil`; it is deliberately absent here.
* `default_trade_for_class()` — the class -> trade map. `vehicle` is dropped as
  an asset class per the migration plan's decision (vehicle maintenance lives in
  the Fleet module's Vehicle doctype only, to avoid double-entry), and `other`
  is dropped because it maps to the `other` trade, which backs no engineering
  role and would only create an asset class nobody is scoped to. Both omissions
  are intentional deviations from the PHP map, not oversights.

Idempotent: existing rows are updated in place, never duplicated, and a row an
administrator has since edited is only corrected on the two fields this patch
owns (`trade_label`/`scoped_role`, `class_label`/`default_trade`).
"""

import frappe

TRADES = [
	# (key, label, scoped_role or None)
	("biomedical", "Biomedical", "Biomedical Engineer"),
	("electrical", "Electrical", "Electrical Engineer"),
	("plumbing", "Plumbing & Sanitary", None),
	("civil", "Civil, Building & Furniture", "Civil Engineer"),
	("mechanical_utility", "Mechanical & Utility Plant", "Mechanical & Utility Engineer"),
	("ac_refrigeration", "AC & Refrigeration", None),
	("it", "IT & Networking", None),
	("housekeeping", "Housekeeping", None),
	("other", "Other", None),
]

ASSET_CLASSES = [
	# (key, label, default_trade)
	("biomedical", "Biomedical Equipment", "biomedical"),
	("furniture", "Furniture & Fixtures", "civil"),
	("infrastructure", "Building & Infrastructure", "civil"),
	("electrical", "Electrical & Power", "electrical"),
	("it", "IT & Communication", "it"),
	("utility", "Utility Plant (Gas / Water / Sewage)", "mechanical_utility"),
]


def _upsert(doctype, name, values):
	if frappe.db.exists(doctype, name):
		doc = frappe.get_doc(doctype, name)
		changed = False
		for field, value in values.items():
			if doc.get(field) != value:
				doc.set(field, value)
				changed = True
		if changed:
			doc.save(ignore_permissions=True)
		return
	payload = {"doctype": doctype}
	payload.update(values)
	frappe.get_doc(payload).insert(ignore_permissions=True)


def execute():
	for key, label, role in TRADES:
		_upsert(
			"Trade",
			key,
			{"trade_name": key, "trade_label": label, "scoped_role": role},
		)

	for key, label, trade in ASSET_CLASSES:
		_upsert(
			"Asset Class",
			key,
			{"class_name": key, "class_label": label, "default_trade": trade},
		)

	frappe.db.commit()
