# Talos Dashboard

A web-based management dashboard for [Talos Linux](https://www.talos.dev/) clusters. Built with Django and Django Channels, it provides a real-time interface for managing nodes, applying machine configurations, running upgrades, and bootstrapping new clusters.

## Features

### Cluster Management
- Add, edit, and delete clusters
- Store and manage talosconfig per cluster
- Download talosconfig and kubeconfig directly from the UI
- Test cluster connectivity
- Refresh node status from the cluster

### Node Management
- View all nodes with their roles, Talos version, and Kubernetes version
- Add new worker or control plane nodes to existing clusters
- Auto-fetch existing machine config from the cluster when adding a new node
- Reboot, shutdown, reset, and restart services on nodes
- View live node logs via WebSocket

### Machine Config
- View and edit the full machine configuration (YAML editor with syntax highlighting)
- Apply machine config changes with selectable apply modes (auto, reboot, staged, etc.)
- Apply JSON patch or YAML merge patch to machine configs

### Patch Templates
- Save named patch templates (JSON RFC 6902 or YAML merge patch format)
- Apply patches to all nodes, control plane only, or worker only
- Select specific target nodes per application
- View real-time console output for each patch job via WebSocket

### Upgrades
- Image upgrade: upgrade Talos OS image on selected nodes with real-time streaming output
- Kubernetes upgrade: upgrade the Kubernetes control plane with streaming logs
- View upgrade job history and console output

### Cluster Bootstrap
- 3-step wizard: enter cluster info, review and edit generated configs, apply to nodes
- Generates `controlplane.yaml` and `worker.yaml` via `talosctl gen config`
- Edit generated YAML before applying (CodeMirror editor)
- Automatically runs `talosctl bootstrap` after config apply
- Manual bootstrap trigger from cluster detail page if needed

### Live Events
- Real-time cluster event stream via WebSocket on the cluster detail page

### Access Control
- Three roles: admin, operator, viewer
- Role-based access enforced on all views and operations

## Stack

- **Backend**: Django 5.x, Django Channels 4.x (WebSocket), Celery
- **Database**: SQLite (default), PostgreSQL (production)
- **Message Broker**: Redis (Celery broker + Channels layer)
- **Frontend**: Bootstrap 5, HTMX, CodeMirror 5
- **CLI**: wraps `talosctl` via subprocess (shell=False throughout)

## Requirements

- Python 3.11+
- Redis
- `talosctl` installed and available in PATH

## Installation

```bash
git clone https://github.com/erelbi/talos-dashboard.git
cd talos-dashboard
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Start Redis

```bash
docker compose up -d
```

Or if Redis is installed locally:

```bash
systemctl start redis
```

### Run migrations

```bash
python manage.py migrate
python manage.py createsuperuser
```

### Start the development server

```bash
python manage.py runserver
```

### Start the Celery worker

In a separate terminal:

```bash
celery -A talos_dashboard worker -l info
```

## Configuration

Settings are in `talos_dashboard/settings/base.py`. The following environment variables are supported:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | insecure default | Django secret key |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |

## Security

- All `talosctl` commands use `subprocess` with `shell=False`
- Talosconfig is written to a temporary file (`/tmp`, mode `0o600`) and deleted after use
- CSRF protection is active on all POST endpoints
- Role checks are enforced via decorators on every view

## URL Structure

| Path | Description |
|---|---|
| `/` | Dashboard overview |
| `/clusters/` | Cluster list |
| `/clusters/<pk>/` | Cluster detail with live events |
| `/clusters/<pk>/nodes/<ip>/` | Node detail and operations |
| `/clusters/<pk>/nodes/<ip>/machineconfig/` | Machine config editor |
| `/upgrades/image/` | Image upgrade |
| `/upgrades/k8s/` | Kubernetes upgrade |
| `/upgrades/jobs/` | Upgrade job list |
| `/patches/` | Patch template list |
| `/patches/<pk>/apply/` | Apply patch to cluster |
| `/patches/jobs/` | Patch job history |
| `/accounts/login/` | Login |

## WebSocket Endpoints

| Path | Description |
|---|---|
| `ws/clusters/<id>/events/` | Live cluster events |
| `ws/clusters/<id>/nodes/<ip>/logs/<service>/` | Node service logs |
| `ws/upgrades/jobs/<id>/progress/` | Upgrade job progress |
| `ws/patches/jobs/<id>/progress/` | Patch job progress |
