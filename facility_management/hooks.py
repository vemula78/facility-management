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
}
