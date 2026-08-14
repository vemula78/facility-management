# PERSISTENCE — where this app's code actually lives on the VM

Written 14-Aug-2026. Applies to the Frappe/ERPNext stack on `sssihms-web-vm2023`
(Azure resource group `SSSIHMS`), deployed via `docker compose -f pwd.yml` in
`/home/azureuser/frappe_docker`. Site name: `frontend`.

## What the mount check found

`docker inspect` on the `backend` container reports exactly two mounts:

| Type | Volume | Container path |
|---|---|---|
| volume | `frappe_docker_sites` | `/home/frappe/frappe-bench/sites` |
| volume | `frappe_docker_logs`  | `/home/frappe/frappe-bench/logs` |

`/home/frappe/frappe-bench/apps` is **not** among them. Application source —
every `hooks.py`, every doctype `.json`, every controller `.py` — sits in the
container's own writable layer.

## What that means

- **Data is safe.** Doctype records live in MariaDB (its own volume) and site
  files live in `frappe_docker_sites`. Neither is at risk from container
  recreation.
- **Code is not.** `docker compose down` followed by `up` with a re-pulled image,
  or any `docker compose pull` + recreate, discards the writable layer. The
  `facility_management` directory disappears; `sites/<site>/site_config` still
  lists the app as installed, and the site then fails to boot with
  `ModuleNotFoundError: No module named 'facility_management'` until the code is
  restored.
- A prior session on this same VM lost work to this exact trap twice (recorded in
  `trust-compliance-demo-docs/APP-CREDENTIALS.md`, "Cosmetic renames"). That is
  why this repo exists.

**Therefore: this GitHub repo, not the container, is the source of truth.**
`https://github.com/vemula78/facility-management` (private). Nothing should be
edited only inside the container; edit here, then deploy.

## A second, related caveat: the app must be present in five containers

`backend`, `queue-short`, `queue-long`, `scheduler`, and `websocket` all run the
same Frappe image but are separate containers with separate writable layers. The
bench-level `sites/apps.txt` is on the shared volume, so all five believe the app
is installed — but only the containers that physically have the code can import
it. Background jobs and the scheduler will crash-loop otherwise.

Whatever you do to `backend`, do to the other four.

## Redeploy / restore procedure

If the containers are recreated from a fresh pull, run this from the VM
(`az vm run-command invoke -g SSSIHMS -n sssihms-web-vm2023 --command-id
RunShellScript`):

```bash
cd /home/azureuser/frappe_docker

# 1. Restore the source into the backend container from this repo.
docker compose -f pwd.yml exec -T -w /home/frappe/frappe-bench backend bash -lc \
  'bench get-app --branch main https://github.com/vemula78/facility-management'
# (private repo: use a PAT in the URL, or docker cp a local clone in instead)

# 2. Copy it to the four sibling containers and pip-install there.
bcid=$(docker compose -f pwd.yml ps -q backend)
rm -rf /tmp/fm_app && docker cp \
  $bcid:/home/frappe/frappe-bench/apps/facility_management /tmp/fm_app
for s in queue-short queue-long scheduler websocket; do
  cid=$(docker compose -f pwd.yml ps -q $s)
  docker exec -u root $cid rm -rf /home/frappe/frappe-bench/apps/facility_management
  docker cp /tmp/fm_app $cid:/home/frappe/frappe-bench/apps/facility_management
  docker exec -u root $cid chown -R frappe:frappe \
    /home/frappe/frappe-bench/apps/facility_management
  docker exec -u frappe $cid bash -lc \
    'cd /home/frappe/frappe-bench && env/bin/pip install -q -e apps/facility_management'
done

# 3. Sync schema. install-app only if the site does not already list it.
docker compose -f pwd.yml exec -T -w /home/frappe/frappe-bench backend bash -lc \
  'bench --site frontend migrate'
```

## The permanent fix (not yet done)

The above is recovery, not prevention. Two durable options, in order of
preference:

1. **Bake the app into a custom image.** Build a `Dockerfile` `FROM` the current
   `frappe/erpnext` tag that runs `bench get-app facility_management <repo>`, push
   it to a registry, and point `pwd.yml` at that image for all five services.
   This is the standard frappe_docker "custom app" path and survives every
   recreate.
2. **Bind-mount an apps directory** from the host into all five services, with
   the repo cloned on the host. Cheaper to set up, but leaves the host as a
   second place that must be backed up.

Until one of those is in place, treat every `docker compose pull`/recreate on
this stack as an event that requires running the restore procedure above.

## Gotchas found while building this app

- `bench new-app` fails at its final `bench build --app` step inside `backend`
  (`node: not found` — assets are built in a different image). The app is fully
  created and pip-installed before that point; the traceback can be ignored, but
  check `apps/facility_management` exists and `env/bin/python -c "import
  facility_management"` succeeds before moving on.
- `facility_management/__init__.py` must contain `__version__ = "0.0.1"`. flit
  refuses to build the package without it, so `pip install -e` fails on every
  sibling container. Do not blank this file.
- `az vm run-command` truncates output **from the front** when it exceeds a few
  KB. Do not try to base64 a whole app tarball out through it; it silently
  returns a corrupt, head-truncated stream.
