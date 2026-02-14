from __future__ import annotations

import csv
import importlib.util
import json
import sys
import types
from pathlib import Path


def load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts/forvo_audio/add_forvo_audio.py"
    fake_scrape_forvo = types.ModuleType("scrape_forvo")
    fake_scrape_forvo.scrape = lambda *args, **kwargs: None  # pragma: no cover
    sys.modules.setdefault("scrape_forvo", fake_scrape_forvo)

    spec = importlib.util.spec_from_file_location("add_forvo_audio", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_tsv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        writer.writerows(rows)


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        assert reader.fieldnames is not None
        return list(reader.fieldnames), list(reader)


def test_extract_query_common_and_edge_cases():
    mod = load_module()
    assert mod.extract_query("noun", "en bil") == "bil"
    assert mod.extract_query("noun", "Ei bok") == "bok"
    assert mod.extract_query("verb", "å spise, spiser, spiste, har spist") == "spise"
    assert mod.extract_query("adjective", "snill") == "snill"
    assert mod.extract_query("expression", "ha det") is None
    assert mod.extract_query("unknown", "ting") is None
    assert mod.extract_query("noun", "") is None


def test_extract_row_query_and_ensure_audio_column():
    mod = load_module()
    row = {"lexical-category": "verb", "norwegian": "å gå, går, gikk, har gått"}
    assert mod.extract_row_query(row) == "gå"
    assert mod.extract_row_query({}) is None

    fields = ["lexical-category", "english"]
    out = mod.ensure_audio_column(fields)
    assert out == ["lexical-category", "english", "audio_file"]
    assert mod.ensure_audio_column(out) == out


def test_path_resolution_and_normalization(tmp_path: Path):
    mod = load_module()
    base = tmp_path
    rel = "audio/forvo_no/no_bank_1_001.mp3"
    abs_path = base / rel
    abs_path.parent.mkdir(parents=True)
    abs_path.write_bytes(b"mp3")

    resolved = mod.resolve_audio_path(rel, base_dir=base)
    assert resolved == abs_path
    assert mod.resolve_audio_path(str(abs_path), base_dir=base) == abs_path
    assert mod.normalize_audio_path(abs_path, base_dir=base) == rel

    outside = tmp_path.parent / "outside.mp3"
    outside.write_bytes(b"x")
    assert mod.normalize_audio_path(outside, base_dir=base) == outside.resolve().as_posix()


def test_build_query_set_and_update_tsv(tmp_path: Path):
    mod = load_module()
    vocab = tmp_path / "vocab.tsv"
    headers = [
        "lexical-category",
        "english",
        "norwegian",
        "pronunciation",
        "example_sentence",
        "audio_file",
    ]
    rows = [
        ["noun", "bank", "en bank", "/b/", "Banken er åpen.", ""],
        ["verb", "go", "å gå, går, gikk, har gått", "/g/", "Jeg går hjem.", ""],
        ["expression", "thanks", "takk", "/t/", "Takk for hjelpen.", ""],
    ]
    write_tsv(vocab, headers, rows)

    assert mod.build_query_set([vocab]) == {"bank", "gå"}
    filled, skipped = mod.update_tsv(
        vocab,
        {"bank": "audio/forvo_no/no_bank_1_001.mp3", "gå": "audio/forvo_no/no_ga_1_001.mp3"},
    )
    assert filled == 2
    assert skipped == 1

    out_headers, out_rows = read_tsv(vocab)
    assert out_headers[-1] == "audio_file"
    assert out_rows[0]["audio_file"] == "audio/forvo_no/no_bank_1_001.mp3"
    assert out_rows[1]["audio_file"] == "audio/forvo_no/no_ga_1_001.mp3"
    assert out_rows[2]["audio_file"] == ""


def test_update_tsv_adds_audio_column_when_missing(tmp_path: Path):
    mod = load_module()
    vocab = tmp_path / "vocab.tsv"
    headers = ["lexical-category", "english", "norwegian", "pronunciation", "example_sentence"]
    rows = [["noun", "book", "en bok", "/b/", "Jeg leser en bok."]]
    write_tsv(vocab, headers, rows)

    filled, skipped = mod.update_tsv(vocab, {"bok": "audio/forvo_no/no_bok_1_001.mp3"})
    assert (filled, skipped) == (1, 0)
    out_headers, out_rows = read_tsv(vocab)
    assert out_headers[-1] == "audio_file"
    assert out_rows[0]["audio_file"] == "audio/forvo_no/no_bok_1_001.mp3"


def test_download_audio_map_reuse_miss_and_download(tmp_path: Path, monkeypatch):
    mod = load_module()
    base = tmp_path
    audio_dir = base / "audio/forvo_no"
    audio_dir.mkdir(parents=True)
    temp_dir = base / "tmp_dl"
    temp_dir.mkdir()
    cache = base / "scripts/forvo_audio/audio_index.json"
    cache.parent.mkdir(parents=True)

    existing = audio_dir / "no_bank_1_001.mp3"
    existing.write_bytes(b"bank")
    cache.write_text(
        json.dumps({"bank": "audio/forvo_no/no_bank_1_001.mp3", "missing": ""}),
        encoding="utf-8",
    )

    downloaded = temp_dir / "no_bok_2_001.mp3"
    downloaded.write_bytes(b"bok")

    def fake_scrape_query(query: str, temp_dir: Path, headed: bool):
        if query == "bok":
            return downloaded
        return None

    monkeypatch.setattr(mod, "scrape_query", fake_scrape_query)

    mapping = mod.download_audio_map(
        queries={"bank", "bok", "missing"},
        temp_dir=temp_dir,
        audio_dir=audio_dir,
        headed=False,
        cache_path=cache,
        workers=1,
        path_base=base,
    )

    assert mapping["bank"] == "audio/forvo_no/no_bank_1_001.mp3"
    assert mapping["missing"] == ""
    assert mapping["bok"] == "audio/forvo_no/no_bok_2_001.mp3"
    assert (audio_dir / "no_bok_2_001.mp3").exists()


def test_download_audio_map_all_reused_does_not_scrape(tmp_path: Path, monkeypatch):
    mod = load_module()
    base = tmp_path
    audio_dir = base / "audio/forvo_no"
    audio_dir.mkdir(parents=True)
    cache = base / "scripts/forvo_audio/audio_index.json"
    cache.parent.mkdir(parents=True)
    temp_dir = base / "tmp_dl"
    temp_dir.mkdir()

    existing = audio_dir / "no_bank_1_001.mp3"
    existing.write_bytes(b"bank")
    cache.write_text(json.dumps({"bank": "audio/forvo_no/no_bank_1_001.mp3"}), encoding="utf-8")

    def should_not_run(*args, **kwargs):
        raise AssertionError("scrape_query should not be called when everything is reused")

    monkeypatch.setattr(mod, "scrape_query", should_not_run)
    mapping = mod.download_audio_map(
        queries={"bank"},
        temp_dir=temp_dir,
        audio_dir=audio_dir,
        headed=False,
        cache_path=cache,
        workers=1,
        path_base=base,
    )
    assert mapping["bank"] == "audio/forvo_no/no_bank_1_001.mp3"


def test_download_audio_map_handles_no_download_and_error(tmp_path: Path, monkeypatch):
    mod = load_module()
    base = tmp_path
    audio_dir = base / "audio/forvo_no"
    audio_dir.mkdir(parents=True)
    cache = base / "scripts/forvo_audio/audio_index.json"
    cache.parent.mkdir(parents=True)
    temp_dir = base / "tmp_dl"
    temp_dir.mkdir()

    def fake_scrape_query(query: str, temp_dir: Path, headed: bool):
        if query == "none":
            return None
        raise RuntimeError("boom")

    monkeypatch.setattr(mod, "scrape_query", fake_scrape_query)
    mapping = mod.download_audio_map(
        queries={"none", "err"},
        temp_dir=temp_dir,
        audio_dir=audio_dir,
        headed=False,
        cache_path=cache,
        workers=1,
        path_base=base,
    )
    assert mapping["none"] == ""
    assert mapping["err"] == ""


def test_load_json_filters_invalid_data(tmp_path: Path):
    mod = load_module()
    path = tmp_path / "cache.json"
    path.write_text(json.dumps({"ok": "v", "bad": 1, 2: "nope"}), encoding="utf-8")
    assert mod.load_json(path) == {"ok": "v", "2": "nope"}
    path.write_text("[]", encoding="utf-8")
    assert mod.load_json(path) == {}
    path.write_text("{", encoding="utf-8")
    assert mod.load_json(path) == {}


def test_main_returns_1_when_no_vocab_files(monkeypatch):
    mod = load_module()
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setattr(mod, "iter_vocab_files", lambda _pattern: [])
    assert mod.main() == 1
