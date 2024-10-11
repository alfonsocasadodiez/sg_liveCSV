import csv
import shotgun_api3
import time

# Connect to ShotGrid
SERVER_URL = "https://{}.shotgrid.autodesk.com"
SCRIPT_NAME = "{}"
SCRIPT_SECRET = "{}"

sg = shotgun_api3.Shotgun(SERVER_URL, SCRIPT_NAME, SCRIPT_SECRET)

# Task and Version fields
task_fields = [{your_task_fields_here}]

version_fields = [{your_version_fields_here}]

# Query the data from ShotGrid
def fetch_data(entity_type, fields):
    filters = [] 
    data = sg.find(entity_type, filters, fields)
    return data

def write_csv(data, file_path='output.csv'):
    if not data:
        print("No data to write.")
        return
    keys = data[0].keys()
    with open(file_path, 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(data)

# Fetch Task and Version data then write to CSV
def export_csv(interval_minutes=10):
    while True:
        print("Fetching Tasks...")
        tasks_data = fetch_data('Task', task_fields)
        write_csv(tasks_data, '/var/www/csv/tasks.csv')
        
        print("Fetching Versions...")
        versions_data = fetch_data('Version', version_fields)
        write_csv(versions_data, '/var/www/csv/versions.csv')
        
        print(f"CSV updated at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(interval_minutes * 60)

export_csv() 
