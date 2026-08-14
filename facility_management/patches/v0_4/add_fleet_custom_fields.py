# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Add this module's custom fields to User and Supplier.

Custom Fields, never edits to core doctype JSON — create_custom_fields is
idempotent, same convention as Equipment Maintenance's add_em_custom_fields.

* `User.fleet_driver` is the fail-closed Fleet Driver identity mapping — see
  fleet.utils.get_user_fleet_driver().
* `Supplier.fleet_vendor_type` / `fleet_credit_facility` / `fleet_monthly_billing`
  carry the PHP prototype's `vendors` collection fields (type, creditFacility,
  monthlyBilling) onto the Supplier doctype Fleet reuses as its vendor master
  — the same doctype AMC/CMC Warranty Contract's `supplier` field and Vehicle's
  `vendor` field both link to.
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"User": [
		{
			"fieldname": "fleet_driver",
			"label": "Fleet Driver",
			"fieldtype": "Link",
			"options": "Fleet Driver",
			"insert_after": "username",
			"description": (
				"The Fleet Driver record this user is identified as. Leaving it blank "
				"is fail-closed: an unmapped Fleet Driver-role user sees nothing."
			),
		}
	],
	"Supplier": [
		{
			"fieldname": "fleet_vendor_type",
			"label": "Fleet Vendor Type",
			"fieldtype": "Select",
			"options": (
				"\nFuel Station\nWorkshop\nDealer\nInsurance\nTowing\n"
				"Certification\nRental Agency\nOther"
			),
			"insert_after": "supplier_group",
		},
		{
			"fieldname": "fleet_credit_facility",
			"label": "Fleet Credit Facility",
			"fieldtype": "Check",
			"insert_after": "fleet_vendor_type",
		},
		{
			"fieldname": "fleet_monthly_billing",
			"label": "Fleet Monthly Billing",
			"fieldtype": "Check",
			"insert_after": "fleet_credit_facility",
		},
	],
}


def execute():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
