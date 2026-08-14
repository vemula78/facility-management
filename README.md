### Facility Management

SSSIHMS facility management — biomedical waste, equipment maintenance, and fleet.

Frappe custom app for the Sri Sathya Sai Institute of Higher Medical Sciences, Whitefield.
The Biomedical Waste module is the pilot; equipment maintenance and fleet follow later.

See `PERSISTENCE.md` for how this app is deployed on the hospital VM and how to restore it
if the Frappe containers are ever recreated from a fresh image pull.

### Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/vemula78/facility-management --branch main
bench --site <site> install-app facility_management
```

### License

MIT
