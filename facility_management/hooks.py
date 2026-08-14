app_name = "facility_management"
app_title = "Facility Management"
app_publisher = "SSSIHMS"
app_description = "SSSIHMS facility management — biomedical waste, equipment maintenance, and fleet"
app_email = "vemula78@gmail.com"
app_license = "mit"

# Document Events
# ---------------
doc_events = {
	"BMW Bag": {
		# BMW records are append-only; hard deletion is blocked outright.
		"on_trash": "facility_management.biomedical_waste.doctype.bmw_bag.bmw_bag.prevent_delete",
	},
}
