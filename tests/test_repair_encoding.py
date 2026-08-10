from hoerspiel_discovery.tasks import repair_encoding


def test_find_pages_with_broken_encoding(monkeypatch, tmp_path):
    series_dir = tmp_path / "series"
    detail_dir = tmp_path / "details"
    series_dir.mkdir()
    detail_dir.mkdir()
    (series_dir / "12.html").write_text("Kaputt �", encoding="utf-8")
    (series_dir / "13.html").write_text("Hörspiel", encoding="utf-8")
    (detail_dir / "https_www_code_650_abc.html").write_text(
        "Sprecher �",
        encoding="utf-8",
    )
    (detail_dir / "https_www_code_651_def.html").write_text(
        "Sprecherin",
        encoding="utf-8",
    )
    monkeypatch.setattr(repair_encoding, "SERIES_PAGES_DIR", series_dir)
    monkeypatch.setattr(repair_encoding, "DETAIL_PAGES_DIR", detail_dir)

    result = repair_encoding.find_pages_with_broken_encoding.fn()

    assert result == {"series_ids": [12], "episode_codes": [650]}


def test_episode_code_from_real_filename_shape(tmp_path):
    path = tmp_path / (
        "https_www_hoerspiele_de_hsp_anzeige_asp_code_16615_abcdef1234.html"
    )

    assert repair_encoding._episode_code_from_filename(path) == 16615
