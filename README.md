# ShotGrid/Flow Production Tracking Live CSV

This project fetches data from ShotGrid/Flow Production Tracking and exports it into CSV files on a schedule.

Two ways to run it:

- **Docker app with a GUI** (recommended) — configure the ShotGrid connection, pick entities/fields straight from your ShotGrid schema, and set the export schedule from a web UI. See [Docker / GUI setup](#docker--gui-setup) below.
- **Standalone script** (`livecsv.py`) — the original minimal script, hand-edited and cron'd. See [Standalone script](#standalone-script) below.

## Docker / GUI setup

### Run it

```bash
docker compose up -d --build
```

Then open `http://localhost:8080`. From there you can:

- Enter your ShotGrid server URL (or just the site name, e.g. `mystudio`), script name and script secret, and test the connection.
- Browse your ShotGrid schema: pick an entity type and the fields to export, straight from ShotGrid (no need to know field names up front).
- Add as many exports as you like (e.g. Tasks, Versions, Shots), each writing its own CSV file.
- Set the refresh interval and trigger an export immediately.

Each configured export is written to `/data/csv/<file_name>.csv` inside the container (a named Docker volume by default) and served at `http://localhost:8080/csv/<file_name>.csv`.

### Configuring via environment variables

Every setting can also be pinned with an environment variable, which overrides whatever is stored from the GUI and is shown there as read-only. This is useful for deploying with secrets from a secret manager instead of typing them into the GUI.

| Variable | Purpose |
| --- | --- |
| `SG_SERVER_URL` | ShotGrid server URL or site name |
| `SG_SCRIPT_NAME` | ShotGrid script user name |
| `SG_SCRIPT_SECRET` | ShotGrid script key |
| `SG_INTERVAL_MINUTES` | Refresh interval in minutes |
| `SG_OUTPUT_DIR` | Directory CSVs are written to (default `/data/csv`) |
| `SG_EXPORTS_JSON` | JSON array fully replacing the export list, e.g. `[{"name":"tasks","entity_type":"Task","fields":["content","sg_status_list"],"file_name":"tasks.csv"}]` |

Set these in `docker-compose.yml` or with `docker run -e ...`.

### Secrets

The ShotGrid script secret is never stored in plaintext. When saved from the GUI it is encrypted with a key (`/data/secret.key`, generated on first run and kept outside of `config.json`) before being written to `/data/config.json`. Keep the `/data` volume private — anyone with both files can still decrypt the secret, same as anyone with access to a `.env` file could.

If `SG_SCRIPT_SECRET` is set as an environment variable, it is used directly and never written to disk at all.

### Data persistence

`/data` holds `config.json`, `secret.key`, and the `csv/` output directory. Mount it as a volume (the provided `docker-compose.yml` already does) so configuration and history survive container restarts.

## Standalone script

The original, minimal script (`livecsv.py`) is kept for reference — a single file you edit directly and run with cron, no GUI or container required.

### Prerequisites

- Python 3.x
- `shotgun_api3` library. Install it via pip:

  ```bash
  pip install shotgun-api3
  ```

### Setup

#### 1. Configure ShotGrid Credentials

Replace the placeholders with your ShotGrid credentials in the script:

```python
SERVER_URL = "https://{your_instance}.shotgrid.autodesk.com"
SCRIPT_NAME = "{your_script_name}"
SCRIPT_SECRET = "{your_token_here}"
```

#### 2. Define Entity Fields

Specify the fields you want to fetch for both Task and Version entities:

```python
task_fields = [{your_task_fields_here}]
version_fields = [{your_version_fields_here}]
```

#### 3. CSV Output Path

By default, CSV files are written to `/var/www/csv/` to be served via Nginx. You can modify the file paths in the `write_csv` function:

```python
write_csv(tasks_data, '/path/to/your/tasks.csv')
write_csv(versions_data, '/path/to/your/versions.csv')
```

### Usage

#### Fetching Data

The script connects to your ShotGrid instance and retrieves data for all projects under the Task and Version entities. This data is then exported into separate CSV files for each entity.

#### Running the Script

The script can be run manually or on a schedule. By default, it fetches data once. To run it periodically, add a number inside the `export_csv()` function and set an interval (in minutes), or set up a crontab schedule (recommended):

### Functions

- **`fetch_data(entity_type, fields)`**: Queries ShotGrid for a specific entity type (e.g., `'Task'`, `'Version'`) and its fields.
  
- **`write_csv(data, file_path)`**: Writes the queried data into a CSV file. You can adjust the file path as needed.

- **`export_csv(interval_minutes)`**: Loops the data-fetching and CSV-writing process at the interval specified (in minutes).

### Automating with Crontab

To automate the script using crontab:

1. Open your crontab configuration:

   ```bash
   $ crontab -e
   ```

2. Add the following entry to run the script every 30 minutes (adjust the path to the script):

   ```bash
   */30 * * * * /usr/bin/python3 /{path_to_script}/liveCSV.py
   ```

### Setting Up Nginx for CSV File Access

The following steps guide you through setting up an HTTP server using Nginx to serve the generated CSV files. It's recommended to configure SSL for secure access.

#### 1. Create Folder and Set Permissions

Create the directory for the CSV files and set appropriate permissions:

```bash
$ mkdir -p /var/www/csv/
$ chmod 755 /var/www/csv/
$ chown www-data:www-data /var/www/csv/
```

#### 2. Modify Nginx Configuration

Edit the default Nginx configuration file (usually located at `/etc/nginx/sites-available/default`) and add the following block:

```nginx
server {
    listen 80;  # Listen on port 80 for HTTP requests
    server_name www.example.com;  # Replace with your domain or IP

    location /csv/ {
        alias /var/www/csv/;  # Directory where your files are stored
        autoindex on;         # Enables directory listing
    }
}
```

#### 3. Restart Nginx

After saving the configuration, restart the Nginx service to apply changes:

```bash
$ sudo systemctl restart nginx
```

#### 4. Accessing the Files

Your CSV files will now be accessible via HTTP:

```
http://www.example.com/csv/{filename.ext}
```

## License

This project is licensed under the MIT License.
