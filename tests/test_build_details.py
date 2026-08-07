import json

import pytest

from hoerspiel_discovery.scraper.fetch_series import build_file_name
from hoerspiel_discovery.tasks import build_details


def _episode(url: str | None = "https://www.hoerspiele.de/hsp_anzeige.asp?code=42"):
    return {
        "url": url,
        "title": "Test Episode",
        "episode_number": 7,
        "series_name": "Serien: Test Series",
        "has_detail_page": url is not None,
    }


def _detail_html() -> str:
    return """
    <html><body>
      <table background="img/backgrounds/BG_hsp_dynamisch.gif"><tr>
        <td width="75%" align="left" valign="top">
          <a href="hsp_serie.asp?serie=1">Test Series</a>
          <a href="hsp_anzeige.asp?code=42">7</a>
          <a href="hsp_anzeige.asp?code=42">Test Episode</a>
          <a href="hsp_serienanzeige.asp?verlag=1">Test Label</a>
        </td>
        <td width="35%" align="justify" valign="top">
          <span class="t4_bold">Beschreibung:</span>
          <span class="t5"> A test description. </span>
          Dauer: 42 Minuten Bestellnummer: ABC-123
        </td>
        <td width="35%" align="left" valign="top">
          <table><tr><td></td><td>Hero</td><td></td><td>Aenne Actor</td></tr></table>
        </td>
      </tr></table>
    </body></html>
    """


def _series_html() -> str:
    return """
    <table><tr>
      <td><a href="hsp_serie.asp?serie=1">Test Series</a></td>
      <td>7</td>
      <td><a href="hsp_anzeige.asp?code=42">Test Episode</a></td>
      <td>Test Label</td>
    </tr></table>
    """


def _valid_record(**overrides):
    record = build_details._build_stub(_episode())
    record.update(overrides)
    return record


def test_parse_episode_parses_and_cleans_detail_html(tmp_path):
    episode = _episode()
    detail_path = tmp_path / build_file_name(episode["url"])
    detail_path.write_text(_detail_html(), encoding="utf-8")

    record, outcome, error = build_details._parse_episode(episode, tmp_path)

    assert outcome == "with_detail"
    assert error is None
    assert record["title"] == "Test Episode"
    assert record["series_name"] == "Test Series"
    assert record["description"] == "A test description."
    assert record["duration_minutes"] == 42.0
    assert record["speakers"] == [{"role": "Hero", "speaker": "Aenne Actor"}]


def test_episode_without_detail_link_becomes_stub(tmp_path):
    record, outcome, error = build_details._parse_episode(_episode(None), tmp_path)

    assert outcome == "stub_without_link"
    assert error is None
    assert record["series_name"] == "Test Series"
    assert record["source_url"] is None


@pytest.mark.parametrize(
    ("create_file", "expected_outcome"),
    [(False, "stub_missing_html"), (True, "stub_parse_error")],
)
def test_missing_or_unusable_detail_html_becomes_stub(
    tmp_path, create_file, expected_outcome
):
    episode = _episode()
    if create_file:
        path = tmp_path / build_file_name(episode["url"])
        path.write_text("<html>not a detail page</html>", encoding="utf-8")

    record, outcome, error = build_details._parse_episode(episode, tmp_path)

    assert outcome == expected_outcome
    assert record["source_url"] == episode["url"]
    assert (error is not None) is create_file


def test_deduplicate_uses_url_and_stub_identity():
    url_record = _valid_record()
    stub = _valid_record(source_url=None)

    result = build_details._deduplicate([url_record, url_record.copy(), stub, stub.copy()])

    assert result == [url_record, stub]


def test_speaker_and_role_normalization_uses_global_frequency():
    records = [
        _valid_record(speakers=[{"speaker": "Aenne Actor", "role": "HELD"}]),
        _valid_record(
            source_url="https://example.test/2",
            speakers=[{"speaker": "Änne Actor", "role": "Held"}],
        ),
        _valid_record(
            source_url="https://example.test/3",
            speakers=[{"speaker": "Änne Actor", "role": "Held"}],
        ),
    ]

    speaker_map = build_details.build_speaker_normalization_map(records)
    role_map = build_details.build_role_normalization_map(records)
    build_details.apply_speaker_normalization(records, speaker_map)
    build_details.apply_role_normalization(records, role_map)

    assert speaker_map == {"Aenne Actor": "Änne Actor"}
    assert role_map == {"HELD": "Held"}
    assert records[0]["speakers"] == [{"speaker": "Änne Actor", "role": "Held"}]


def test_validation_rejects_empty_and_duplicate_records():
    with pytest.raises(ValueError, match="no records"):
        build_details._validate_records([])

    record = _valid_record()
    with pytest.raises(ValueError, match="duplicate source_key"):
        build_details._validate_records([record, record.copy()])


def test_source_keys_are_stable_and_distinguish_episode_types():
    linked = _valid_record()
    same_linked = linked.copy()
    stub = _valid_record(source_url=None)
    stub["source_key"] = build_details._build_source_key(stub)

    assert linked["source_key"] == "hoerspiele.de:episode:42"
    assert build_details._build_source_key(same_linked) == linked["source_key"]
    assert stub["source_key"].startswith("hoerspiele.de:stub:")
    assert build_details._build_source_key(stub) == stub["source_key"]
    assert stub["source_key"] != linked["source_key"]


def test_publish_replaces_final_file_only_after_validation(monkeypatch, tmp_path):
    monkeypatch.setattr(build_details, "INTERIM_DATA_DIR", tmp_path)
    final_path = tmp_path / "cleaned_details.json"
    final_path.write_text('[{"old": true}]', encoding="utf-8")
    candidate_path = tmp_path / "cleaned_details_candidate.json"
    records = [_valid_record()]
    candidate_path.write_text(json.dumps(records), encoding="utf-8")
    candidate_result = {
        "path": str(candidate_path),
        "parse_stats": {"parse_errors": []},
        "normalization": {"speaker_mappings": 0, "role_mappings": 0},
    }

    result = build_details.validate_and_publish_details.fn(candidate_result)

    assert result["path"] == str(final_path)
    assert json.loads(final_path.read_text(encoding="utf-8")) == records
    assert not candidate_path.exists()

    invalid_candidate = tmp_path / "cleaned_details_candidate.json"
    invalid_candidate.write_text("[]", encoding="utf-8")
    candidate_result["path"] = str(invalid_candidate)
    with pytest.raises(ValueError, match="no records"):
        build_details.validate_and_publish_details.fn(candidate_result)
    assert json.loads(final_path.read_text(encoding="utf-8")) == records


def test_complete_file_based_pipeline(monkeypatch, tmp_path):
    series_dir = tmp_path / "raw" / "series_pages"
    detail_dir = tmp_path / "raw" / "detail_pages"
    interim_dir = tmp_path / "interim"
    series_dir.mkdir(parents=True)
    detail_dir.mkdir(parents=True)
    (series_dir / "1.html").write_text(_series_html(), encoding="utf-8")
    url = "https://www.hoerspiele.de/hsp_anzeige.asp?code=42"
    (detail_dir / build_file_name(url)).write_text(_detail_html(), encoding="utf-8")
    monkeypatch.setattr(build_details, "RAW_SERIES_PAGES_DIR", series_dir)
    monkeypatch.setattr(build_details, "RAW_DETAIL_PAGES_DIR", detail_dir)
    monkeypatch.setattr(build_details, "INTERIM_DATA_DIR", interim_dir)

    staging = build_details.parse_and_clean_details.fn()
    candidate = build_details.normalize_details.fn(staging)
    result = build_details.validate_and_publish_details.fn(candidate)

    output_path = interim_dir / "cleaned_details.json"
    records = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["validation"]["records"] == 1
    assert result["validation"]["stubs"] == 0
    assert records[0]["title"] == "Test Episode"
    assert (interim_dir / "cleaned_details_staging.json").exists()
    assert not (interim_dir / "cleaned_details_candidate.json").exists()
