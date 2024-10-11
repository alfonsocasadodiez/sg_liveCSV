# ShotGrid/Flow Production Tracking Live CSV Script

This script fetches data from ShotGrid/Flow Production Tracking and exports it into CSV files, one per entity type (Task and Version as created, modify it to your liking :)). It can be set to run at a specified interval, automatically updating the CSV files, then exposed via a Nginx web server. 

## Prerequisites

- Python 3.x
- `shotgun_api3` library. Install it via pip:

  ```bash
  pip install shotgun-api3
  ```

## Setup

### 1. Configure ShotGrid Credentials

Replace the placeholders with your ShotGrid credentials in the script:

```python
SERVER_URL = "https://{your_instance}.shotgrid.autodesk.com"
SCRIPT_NAME = "{your_script_name}"
SCRIPT_SECRET = "{your_token_here}"
```

### 2. Define Entity Fields

Specify the fields you want to fetch for both Task and Version entities:

```python
task_fields = [{your_task_fields_here}]
version_fields = [{your_version_fields_here}]
```

### 3. CSV Output Path

By default, CSV files are written to `/var/www/csv/` to be served via Nginx. You can modify the file paths in the `write_csv` function:

```python
write_csv(tasks_data, '/path/to/your/tasks.csv')
write_csv(versions_data, '/path/to/your/versions.csv')
```

## Usage

### Fetching Data

The script connects to your ShotGrid instance and retrieves data for all projects under the Task and Version entities. This data is then exported into separate CSV files for each entity.

### Running the Script

The script can be run manually or on a schedule. By default, it fetches data once. To run it periodically, add a number inside the `export_csv()` function and set an interval (in minutes), or set up a crontab schedule (recommended):

## Functions

- **`fetch_data(entity_type, fields)`**: Queries ShotGrid for a specific entity type (e.g., `'Task'`, `'Version'`) and its fields.
  
- **`write_csv(data, file_path)`**: Writes the queried data into a CSV file. You can adjust the file path as needed.

- **`export_csv(interval_minutes)`**: Loops the data-fetching and CSV-writing process at the interval specified (in minutes).

## Automating with Crontab

To automate the script using crontab:

1. Open your crontab configuration:

   ```bash
   $ crontab -e
   ```

2. Add the following entry to run the script every 30 minutes (adjust the path to the script):

   ```bash
   */30 * * * * /usr/bin/python3 /{path_to_script}/liveCSV.py
   ```

## Setting Up Nginx for CSV File Access

The following steps guide you through setting up an HTTP server using Nginx to serve the generated CSV files. It's recommended to configure SSL for secure access.

### 1. Create Folder and Set Permissions

Create the directory for the CSV files and set appropriate permissions:

```bash
$ mkdir -p /var/www/csv/
$ chmod 755 /var/www/csv/
$ chown www-data:www-data /var/www/csv/
```

### 2. Modify Nginx Configuration

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

### 3. Restart Nginx

After saving the configuration, restart the Nginx service to apply changes:

```bash
$ sudo systemctl restart nginx
```

### 4. Accessing the Files

Your CSV files will now be accessible via HTTP:

```
http://www.example.com/csv/{filename.ext}
```

## License

This project is licensed under the MIT License.
