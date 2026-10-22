"""Thin wrapper around shotgun_api3 for connecting, schema introspection, and querying data."""
import shotgun_api3


def connect(connection: dict) -> shotgun_api3.Shotgun:
    server_url = connection["server_url"]
    if server_url and not server_url.startswith("http"):
        server_url = f"https://{server_url}.shotgrid.autodesk.com"
    return shotgun_api3.Shotgun(server_url, connection["script_name"], connection["script_secret"])


def list_entity_types(connection: dict):
    sg = connect(connection)
    schema = sg.schema_entity_read()
    entities = []
    for entity_type, info in schema.items():
        display_name = (info.get("name") or {}).get("value") or entity_type
        entities.append({"entity_type": entity_type, "display_name": display_name})
    entities.sort(key=lambda e: e["display_name"].lower())
    return entities


def list_entity_fields(connection: dict, entity_type: str):
    sg = connect(connection)
    schema = sg.schema_field_read(entity_type)
    fields = []
    for field_name, info in schema.items():
        display_name = (info.get("name") or {}).get("value") or field_name
        data_type = (info.get("data_type") or {}).get("value") or ""
        fields.append({"field_name": field_name, "display_name": display_name, "data_type": data_type})
    fields.sort(key=lambda f: f["display_name"].lower())
    return fields


def test_connection(connection: dict):
    sg = connect(connection)
    info = sg.info()
    return {"ok": True, "server_info": info}


def fetch_data(connection: dict, entity_type: str, fields: list, filters=None):
    sg = connect(connection)
    return sg.find(entity_type, filters or [], fields)
