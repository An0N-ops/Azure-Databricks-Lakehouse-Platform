def test_columns_match_config(small_config, small_data):
    for entity, rows in small_data.items():
        expected = {field["name"] for field in small_config["entities"][entity]["fields"]}
        actual = set(rows[0].keys())
        assert actual == expected, f"{entity} schema mismatch"


def test_id_columns_are_strings(small_config, small_data):
    for entity, rows in small_data.items():
        for field in small_config["entities"][entity]["fields"]:
            if field["type"] == "id":
                assert all(isinstance(row[field["name"]], str) for row in rows)


def test_int_range_produces_ints(small_config, small_data):
    for entity, rows in small_data.items():
        for field in small_config["entities"][entity]["fields"]:
            if field["type"] == "int_range":
                assert all(isinstance(row[field["name"]], int) for row in rows)


def test_float_range_produces_floats(small_config, small_data):
    for entity, rows in small_data.items():
        for field in small_config["entities"][entity]["fields"]:
            if field["type"] == "float_range":
                assert all(isinstance(row[field["name"]], float) for row in rows)


def test_constant_fields_match_value(small_config, small_data):
    for entity, rows in small_data.items():
        for field in small_config["entities"][entity]["fields"]:
            if field["type"] == "constant":
                assert all(row[field["name"]] == field["value"] for row in rows)


def test_dates_parse(small_data):
    for row in small_data["weather"]:
        assert isinstance(row["observed_date"], str)
    for row in small_data["work_orders"]:
        assert isinstance(row["opened_at"], str)
