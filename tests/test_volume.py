def _expected_count(config, entity, data):
    volume = config["entities"][entity]["volume"]
    if isinstance(volume, int):
        return volume
    reference_rows = len(data[volume["rows_per_reference"]])
    return reference_rows * volume["rows_per_unit"]


def test_counts_match_config(small_config, small_data):
    for entity, rows in small_data.items():
        assert len(rows) == _expected_count(small_config, entity, small_data), entity


def test_reference_volume_tracks_parent(small_config, small_data):
    iot = small_data["iot_events"]
    assert len(iot) == len(small_data["assets"]) * 4


def test_manifest_counts(small_data, industry_config):
    assert len(small_data["work_orders"]) == 40
    assert len(small_data["regions"]) == 6
