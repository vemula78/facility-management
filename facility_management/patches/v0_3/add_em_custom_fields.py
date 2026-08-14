# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Add this module's custom fields to the standard Asset and User doctypes.

Custom Fields, never edits to core doctype JSON — `create_custom_fields` is
idempotent (it updates an existing field in place rather than duplicating it),
so re-running `bench migrate` is safe.

* `Asset.hem_asset_class` is the field the whole trade-scoping layer keys off.
* `User.hem_department` is the fail-closed department mapping, ported from the
  WordPress `hem_department` user meta. It links to ERPNext's own HR
  `Department` doctype rather than introducing a parallel department register.
* `Asset.hem_amc_cmc_expiry` is denormalized from AMC CMC Warranty Contract
  (see that doctype's on_update/on_cancel/on_trash hooks) — the MAX end_date
  across the asset's non-cancelled contracts, maintained server-side rather
  than computed on read.
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Asset": [
		{
			"fieldname": "hem_asset_class",
			"label": "Asset Class",
			"fieldtype": "Link",
			"options": "Asset Class",
			"insert_after": "asset_category",
			"description": (
				"Maintenance asset class. Determines which engineering trade owns this "
				"asset, and therefore which engineering role can see it."
			),
		},
		{
			"fieldname": "hem_amc_cmc_expiry",
			"label": "AMC/CMC/Warranty Expiry",
			"fieldtype": "Date",
			"insert_after": "hem_asset_class",
			"read_only": 1,
			"description": (
				"Latest end_date across this asset's non-cancelled AMC/CMC/Warranty "
				"Contract rows. Maintained by the Contract doctype's controller — "
				"never set directly."
			),
		},
	],
	"User": [
		{
			"fieldname": "hem_department",
			"label": "Facility Department",
			"fieldtype": "Link",
			"options": "Department",
			"insert_after": "username",
			"description": (
				"Department this user raises and views facility records for. Leaving it "
				"blank is fail-closed: an unmapped department user sees nothing."
			),
		}
	],
}


def execute():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
