# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""AMC/CMC/Warranty Contract — the one Contract doctype backing all three
contract types (HEM tracked them as a single vendor-contract concept keyed by
contract_type, and this doctype keeps that shape rather than splitting into
three near-identical doctypes).

Maintains Asset.hem_amc_cmc_expiry server-side: it must always equal the MAX
end_date across every non-cancelled (docstatus != 2) Contract row for that
asset. Three paths change that set of rows and all three are wired via
doc_events in hooks.py, mirroring the on_trash pattern already used for BMW
and Trade/Asset Class in this app:

* on_update — fires on both insert and every save (including a submit), so a
  new contract or an edited end_date/asset is picked up without a separate
  after_insert hook.
* on_cancel — a cancelled contract must stop counting even though its row
  still exists.
* on_trash — a deleted contract's row disappears entirely; on_trash fires
  before the row is actually removed from the database, so the recompute
  must exclude the document being deleted by name rather than relying on the
  DB no longer containing it.
"""

import frappe
from frappe.model.document import Document


class AMCCMCWarrantyContract(Document):
	pass


def recompute_asset_amc_cmc_expiry(asset, exclude_name=None):
	"""Set Asset.hem_amc_cmc_expiry to the MAX end_date of `asset`'s non-cancelled
	contracts, excluding `exclude_name` (the contract mid-delete, whose row is
	still physically present when on_trash calls this). None when there are none
	left — a missing expiry, not a stale or fabricated one."""
	if not asset:
		return
	filters = {"asset": asset, "docstatus": ["!=", 2]}
	if exclude_name:
		filters["name"] = ["!=", exclude_name]
	expiry = frappe.db.get_value("AMC CMC Warranty Contract", filters, "MAX(end_date)")
	frappe.db.set_value("Asset", asset, "hem_amc_cmc_expiry", expiry, update_modified=False)


def update_asset_expiry(doc, method=None):
	"""on_update: recompute for the contract's current asset, and also for its
	previous asset if the `asset` link itself was changed on this save — otherwise
	the old asset would be left showing an expiry from a contract no longer
	linked to it."""
	recompute_asset_amc_cmc_expiry(doc.asset)
	previous = doc.get_doc_before_save()
	if previous and previous.asset and previous.asset != doc.asset:
		recompute_asset_amc_cmc_expiry(previous.asset)


def cancel_asset_expiry(doc, method=None):
	"""on_cancel: this document's own docstatus is already 2 by the time this
	hook runs, but exclude_name is passed anyway so the recompute is correct
	regardless of exactly when the docstatus write lands relative to the hook."""
	recompute_asset_amc_cmc_expiry(doc.asset, exclude_name=doc.name)


def delete_asset_expiry(doc, method=None):
	"""on_trash: the row still exists in the database at this point, so it must
	be excluded by name rather than relied upon to already be gone."""
	recompute_asset_amc_cmc_expiry(doc.asset, exclude_name=doc.name)
