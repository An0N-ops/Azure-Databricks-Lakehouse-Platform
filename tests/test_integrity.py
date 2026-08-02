def _fk_fields(config, entity):
    return [
        field for field in config["entities"][entity]["fields"] if field["type"] == "foreign_key"
    ]


def _id_columns(config, entity):
    return [
        field["name"] for field in config["entities"][entity]["fields"] if field["type"] == "id"
    ]


def test_ids_unique_per_entity(small_data, industry_config):
    for entity, rows in small_data.items():
        for column in _id_columns(industry_config, entity):
            values = [row[column] for row in rows]
            assert len(values) == len(set(values)), f"{entity}.{column} has duplicates"


def test_foreign_keys_resolve(small_data, industry_config):
    for entity, rows in small_data.items():
        for field in _fk_fields(industry_config, entity):
            ref_values = {row[field["column"]] for row in small_data[field["entity"]]}
            for row in rows:
                value = row[field["name"]]
                assert value is None or value in ref_values, (
                    f"{entity}.{field['name']}={value!r} not in {field['entity']}"
                )


def test_work_order_hours_only_when_completed(small_data):
    for row in small_data["work_orders"]:
        if row["status_code"] != "COMPLETED":
            assert row["actual_hours"] is None
            assert row["completed_at"] is None
        else:
            assert row["actual_hours"] is not None


def test_employee_email_matches_names(small_data):
    for row in small_data["employees"]:
        expected = f"{row['first_name']}.{row['last_name']}@northgridresources.com"
        assert row["email"] == expected


def test_sensor_unit_matches_type(small_data):
    units = {
        "Pressure": "psi",
        "Temperature": "degC",
        "Flow": "m3/h",
        "Level": "%",
        "Vibration": "mm/s",
    }
    for row in small_data["iot_events"]:
        assert row["unit"] == units[row["sensor_type"]]


def test_iot_reading_within_sensor_bounds(small_data):
    bounds = {
        "Pressure": (200, 5000),
        "Temperature": (-20, 250),
        "Flow": (0, 1200),
        "Level": (0, 100),
        "Vibration": (0, 50),
    }
    for row in small_data["iot_events"]:
        lo, hi = bounds[row["sensor_type"]]
        assert lo <= row["reading"] <= hi


def test_work_order_description_references_work_type(small_data):
    for row in small_data["work_orders"]:
        assert row["work_type"] in row["description"]
