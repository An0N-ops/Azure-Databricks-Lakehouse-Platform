from pathlib import Path

from sample_data.cli import main

INDUSTRIES_DIR = Path(__file__).resolve().parents[1] / "sample-data" / "sample_data" / "industries"


def test_generate_cli_smoke(tmp_path, capsys):
    exit_code = main(
        [
            "generate",
            "--industry",
            "energy",
            "--config-dir",
            str(INDUSTRIES_DIR),
            "--output",
            str(tmp_path),
            "--seed",
            "1",
            "--scale",
            "0.01",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Generated 14 entities" in captured.out
    assert (tmp_path / "energy" / "manifest.json").is_file()


def test_generate_cli_with_explicit_dates(tmp_path):
    exit_code = main(
        [
            "generate",
            "--industry",
            "energy",
            "--config-dir",
            str(INDUSTRIES_DIR),
            "--output",
            str(tmp_path),
            "--seed",
            "1",
            "--scale",
            "0.01",
            "--start-date",
            "2025-01-01",
            "--end-date",
            "2025-12-31",
            "--as-of-date",
            "2025-12-31",
        ]
    )
    assert exit_code == 0
    assert (tmp_path / "energy" / "iot_events" / "batch_date=2025-12-31").is_dir()


def test_list_cli(capsys):
    exit_code = main(["list", "--config-dir", str(INDUSTRIES_DIR)])
    assert exit_code == 0
    assert "energy" in capsys.readouterr().out


def test_generate_unknown_industry(tmp_path):
    exit_code = main(
        [
            "generate",
            "--industry",
            "mining",
            "--config-dir",
            str(INDUSTRIES_DIR),
            "--output",
            str(tmp_path),
        ]
    )
    assert exit_code == 1


def test_generate_invalid_date(tmp_path):
    exit_code = main(
        [
            "generate",
            "--industry",
            "energy",
            "--config-dir",
            str(INDUSTRIES_DIR),
            "--output",
            str(tmp_path),
            "--start-date",
            "not-a-date",
        ]
    )
    assert exit_code == 1


def test_generate_invalid_scale(tmp_path):
    exit_code = main(
        [
            "generate",
            "--industry",
            "energy",
            "--config-dir",
            str(INDUSTRIES_DIR),
            "--output",
            str(tmp_path),
            "--scale",
            "-1",
        ]
    )
    assert exit_code == 1
