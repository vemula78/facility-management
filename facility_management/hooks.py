app_name = "facility_management"
app_title = "Facility Management"
app_publisher = "SSSIHMS"
app_description = "SSSIHMS facility management — biomedical waste, equipment maintenance, and fleet"
app_email = "vemula78@gmail.com"
app_license = "mit"

# Website Route Rules
# --------------------
# Maps the required public route (with hyphens, matching the original plugin's
# /biomedical-waste-management/ URL) onto the www/ page file (underscores, since
# Python module names can't contain hyphens).
website_route_rules = [
	{"from_route": "/biomedical-waste-management", "to_route": "biomedical_waste_management"},
]

# Permissions — fail-closed trade scoping (Equipment Maintenance)
# ---------------------------------------------------------------
# Frappe User Permissions fail OPEN (no rows = unrestricted), so scoping lives in
# code. BOTH hooks are required: query conditions filter list views, has_permission
# gates a direct /api/resource/Asset/<name> fetch that list filters never see.
# This Asset pair is the reference pattern for PM/Ticket/Contract/Requisition.
permission_query_conditions = {
	"Asset": "facility_management.equipment_maintenance.permissions.asset_query_conditions",
}

has_permission = {
	"Asset": "facility_management.equipment_maintenance.permissions.asset_has_permission",
}

# Fixtures
# --------
# The custom fields added by add_em_custom_fields.py must also be declared here
# so `bench export-fixtures` / standard fixture sync doesn't miss them on a site
# that doesn't run this app's own patches.
fixtures = [
	{
		"dt": "Custom Field",
		"filters": [["name", "in", ["Asset-hem_asset_class", "User-hem_department"]]],
	},
]

# Seed data lifecycle
# --------------------
# Trade / Asset Class master data is idempotent (upsert-by-name), so it's safe
# to also run on after_install (fresh site) and after_migrate (site that
# bypassed or reset the one-off patch in patches.txt).
after_install = "facility_management.patches.v0_3.seed_em_trades_and_asset_classes.execute"
after_migrate = "facility_management.patches.v0_3.seed_em_trades_and_asset_classes.execute"

# Document Events
# ---------------
doc_events = {
	"BMW Bag": {
		# BMW records are append-only; hard deletion is blocked outright.
		"on_trash": "facility_management.biomedical_waste.doctype.bmw_bag.bmw_bag.prevent_delete",
	},
	"BMW Bed-Day Record": {
		"on_trash": "facility_management.biomedical_waste.doctype.bmw_bed_day_record.bmw_bed_day_record.prevent_delete",
	},
	"BMW Accident": {
		"on_trash": "facility_management.biomedical_waste.doctype.bmw_accident.bmw_accident.prevent_delete",
	},
	"BMW Handover": {
		# A cancelled handover still carries the void reason, manifest number and
		# receiver acknowledgement — it is a record, not scrap.
		"on_trash": "facility_management.biomedical_waste.doctype.bmw_handover.bmw_handover.prevent_delete",
	},
	"BMW Department": {
		# Deleting a department would orphan the `department` link on historical bags.
		"on_trash": "facility_management.biomedical_waste.doctype.bmw_department.bmw_department.prevent_delete",
	},
	"Trade": {
		"on_trash": "facility_management.equipment_maintenance.doctype.trade.trade.prevent_delete",
	},
	"Asset Class": {
		"on_trash": "facility_management.equipment_maintenance.doctype.asset_class.asset_class.prevent_delete",
	},
}
