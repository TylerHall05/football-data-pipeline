from football_pipeline.extract import parse_raw_csv


def test_parses_fixture_and_drops_blank_rows(sample_csv_bytes):
    frame = parse_raw_csv(sample_csv_bytes, "2425", "E0")
    assert len(frame) == 15  # 16 data lines minus the fully blank one
    assert frame.loc[0, "league_code"] == "E0"
    assert frame.loc[0, "season"] == "2425"
    assert frame.loc[0, "HomeTeam"] == "Man United"


def test_values_are_kept_as_text(sample_csv_bytes):
    frame = parse_raw_csv(sample_csv_bytes, "2425", "E0")
    assert frame.loc[0, "FTHG"] == "1"
    assert frame.loc[0, "Date"] == "16/08/2024"


def test_handles_utf8_bom():
    content = b"\xef\xbb\xbfDiv,HomeTeam\nE0,Arsenal\n"
    frame = parse_raw_csv(content, "2425", "E0")
    assert "Div" in frame.columns


def test_falls_back_to_latin1():
    content = "Div,Referee\nE0,José\n".encode("latin-1")
    frame = parse_raw_csv(content, "2425", "E0")
    assert frame.loc[0, "Referee"] == "José"


def test_drops_unnamed_trailing_columns():
    content = b"Div,HomeTeam,\nE0,Arsenal,\n"
    frame = parse_raw_csv(content, "2425", "E0")
    assert not any(c.startswith("Unnamed") for c in frame.columns)
