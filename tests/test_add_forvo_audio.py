from __future__ import annotations

import csv
import importlib.util
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def mod():
    script_path = Path(__file__).resolve().parents[1] / "scripts/forvo_audio/add_forvo_audio.py"
    fake_scrape_forvo = types.ModuleType("scrape_forvo")
    fake_scrape_forvo.scrape = lambda *args, **kwargs: None  # pragma: no cover
    sys.modules.setdefault("scrape_forvo", fake_scrape_forvo)
    sys.path.insert(0, str(script_path.parent))

    spec = importlib.util.spec_from_file_location("add_forvo_audio", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def downloader_module(mod):
    import forvo_download

    return forvo_download


def write_tsv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(headers)
        writer.writerows(rows)


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        assert reader.fieldnames is not None
        return list(reader.fieldnames), list(reader)


def test_extract_query_common_and_edge_cases(mod):
    assert mod.extract_query("noun", "en bil") == "bil"
    assert mod.extract_query("noun", "Ei bok") == "bok"
    assert mod.extract_query("verb", "å spise, spiser, spiste, har spist") == "spise"
    assert mod.extract_query("adjective", "snill") == "snill"
    assert mod.extract_query("expression", "ha det") is None
    assert mod.extract_query("unknown", "ting") is None
    assert mod.extract_query("noun", "") is None


def test_extract_row_query_and_ensure_audio_column(mod):
    row = {"lexical-category": "verb", "norwegian": "å gå, går, gikk, har gått"}
    assert mod.extract_row_query(row) == "gå"
    assert mod.extract_row_query({}) is None

    fields = ["lexical-category", "english"]
    out = mod.ensure_audio_column(fields)
    assert out == ["lexical-category", "english", "audio_file"]
    assert mod.ensure_audio_column(out) == out


def test_path_resolution_and_normalization(mod, tmp_path: Path):
    base_dir = tmp_path
    rel = "audio/forvo_no/no_bank_1_001.mp3"
    abs_path = base_dir / rel
    abs_path.parent.mkdir(parents=True)
    abs_path.write_bytes(b"mp3")

    assert mod.resolve_audio_path(rel, base_dir=base_dir) == abs_path
    assert mod.resolve_audio_path(str(abs_path), base_dir=base_dir) == abs_path
    assert mod.normalize_audio_path(abs_path, base_dir=base_dir) == rel

    outside = tmp_path.parent / "outside.mp3"
    outside.write_bytes(b"x")
    assert mod.normalize_audio_path(outside, base_dir=base_dir) == outside.resolve().as_posix()


def test_build_query_set_and_update_tsv(mod, tmp_path: Path):
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
    filled, empty = mod.update_tsv(
        vocab,
        {"bank": "audio/forvo_no/no_bank_1_001.mp3", "gå": "audio/forvo_no/no_ga_1_001.mp3"},
    )
    assert (filled, empty) == (2, 1)

    out_headers, out_rows = read_tsv(vocab)
    assert out_headers[-1] == "audio_file"
    assert out_rows[0]["audio_file"] == "audio/forvo_no/no_bank_1_001.mp3"
    assert out_rows[1]["audio_file"] == "audio/forvo_no/no_ga_1_001.mp3"
    assert out_rows[2]["audio_file"] == ""


def test_build_audio_map_from_vocab(mod, tmp_path: Path):
    base_dir = tmp_path
    audio_file = base_dir / "audio/forvo_no/no_bank_1_001.mp3"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"bank")

    vocab = base_dir / "vocab.tsv"
    write_tsv(
        vocab,
        [
            "lexical-category",
            "english",
            "norwegian",
            "pronunciation",
            "example_sentence",
            "audio_file",
        ],
        [
            ["noun", "bank", "en bank", "/b/", "Banken er åpen.", "audio/forvo_no/no_bank_1_001.mp3"],
            ["verb", "go", "å gå, går, gikk, har gått", "/g/", "Jeg går hjem.", ""],
        ],
    )

    audio_map = mod.build_audio_map_from_vocab([vocab], base_dir=base_dir)
    assert audio_map == {"bank": "audio/forvo_no/no_bank_1_001.mp3"}


def test_build_audio_map_from_vocab_ignores_null_audio(mod, tmp_path: Path):
    base_dir = tmp_path
    vocab = base_dir / "vocab.tsv"
    write_tsv(
        vocab,
        [
            "lexical-category",
            "english",
            "norwegian",
            "pronunciation",
            "example_sentence",
            "audio_file",
        ],
        [
            ["noun", "book", "en bok", "/b/", "Jeg leser en bok.", "null"],
        ],
    )

    audio_map = mod.build_audio_map_from_vocab([vocab], base_dir=base_dir)
    assert audio_map == {}


def test_update_tsv_adds_audio_column_when_missing(mod, tmp_path: Path):
    vocab = tmp_path / "vocab.tsv"
    headers = ["lexical-category", "english", "norwegian", "pronunciation", "example_sentence"]
    rows = [["noun", "book", "en bok", "/b/", "Jeg leser en bok."]]
    write_tsv(vocab, headers, rows)

    filled, empty = mod.update_tsv(vocab, {"bok": "audio/forvo_no/no_bok_1_001.mp3"})
    assert (filled, empty) == (1, 0)

    out_headers, out_rows = read_tsv(vocab)
    assert out_headers[-1] == "audio_file"
    assert out_rows[0]["audio_file"] == "audio/forvo_no/no_bok_1_001.mp3"


def test_update_tsv_uses_empty_audio_for_unresolved_entries(mod, tmp_path: Path):
    vocab = tmp_path / "vocab.tsv"
    headers = ["lexical-category", "english", "norwegian", "pronunciation", "example_sentence"]
    rows = [
        ["noun", "book", "en bok", "/b/", "Jeg leser en bok."],
        ["expression", "thanks", "takk", "/t/", "Takk for hjelpen."],
    ]
    write_tsv(vocab, headers, rows)

    filled, empty = mod.update_tsv(vocab, {})
    assert (filled, empty) == (0, 2)

    out_headers, out_rows = read_tsv(vocab)
    assert out_headers[-1] == "audio_file"
    for row in out_rows:
        assert row["audio_file"] == "" or row["audio_file"].startswith("audio/")


def test_download_audio_map_reuse_and_download(mod, downloader_module, tmp_path: Path, monkeypatch):
    base_dir = tmp_path
    audio_dir = base_dir / "audio/forvo_no"
    audio_dir.mkdir(parents=True)
    temp_dir = base_dir / "tmp_dl"
    temp_dir.mkdir()

    existing = audio_dir / "no_bank_1_001.mp3"
    existing.write_bytes(b"bank")

    downloaded = temp_dir / "no_bok_2_001.mp3"
    downloaded.write_bytes(b"bok")

    def fake_scrape_query_with_timeout(query: str, **kwargs):
        if query == "bok":
            return downloaded, None, False
        return None, None, False

    monkeypatch.setattr(downloader_module, "scrape_query_with_timeout", fake_scrape_query_with_timeout)

    mapping = mod.download_audio_map(
        queries={"bank", "bok", "missing"},
        temp_dir=temp_dir,
        audio_dir=audio_dir,
        headed=False,
        workers=1,
        base_dir=base_dir,
        initial_map={"bank": "audio/forvo_no/no_bank_1_001.mp3"},
    )

    assert mapping["bank"] == "audio/forvo_no/no_bank_1_001.mp3"
    assert mapping["bok"] == "audio/forvo_no/no_bok_2_001.mp3"
    assert "missing" not in mapping
    assert (audio_dir / "no_bok_2_001.mp3").exists()


def test_download_audio_map_all_reused_does_not_scrape(mod, downloader_module, tmp_path: Path, monkeypatch):
    base_dir = tmp_path
    audio_dir = base_dir / "audio/forvo_no"
    audio_dir.mkdir(parents=True)
    temp_dir = base_dir / "tmp_dl"
    temp_dir.mkdir()

    existing = audio_dir / "no_bank_1_001.mp3"
    existing.write_bytes(b"bank")

    def should_not_run(*args, **kwargs):
        raise AssertionError("scrape_query_with_timeout should not be called when everything is reused")

    monkeypatch.setattr(downloader_module, "scrape_query_with_timeout", should_not_run)
    mapping = mod.download_audio_map(
        queries={"bank"},
        temp_dir=temp_dir,
        audio_dir=audio_dir,
        headed=False,
        workers=1,
        base_dir=base_dir,
        initial_map={"bank": "audio/forvo_no/no_bank_1_001.mp3"},
    )
    assert mapping["bank"] == "audio/forvo_no/no_bank_1_001.mp3"


def test_download_audio_map_handles_no_download_and_error(mod, downloader_module, tmp_path: Path, monkeypatch):
    base_dir = tmp_path
    audio_dir = base_dir / "audio/forvo_no"
    audio_dir.mkdir(parents=True)
    temp_dir = base_dir / "tmp_dl"
    temp_dir.mkdir()

    def fake_scrape_query_with_timeout(query: str, **kwargs):
        if query == "none":
            return None, None, False
        return None, "boom", False

    monkeypatch.setattr(downloader_module, "scrape_query_with_timeout", fake_scrape_query_with_timeout)
    mapping = mod.download_audio_map(
        queries={"none", "err"},
        temp_dir=temp_dir,
        audio_dir=audio_dir,
        headed=False,
        workers=1,
        base_dir=base_dir,
    )
    assert mapping == {}


def test_download_audio_map_handles_timeout(mod, downloader_module, tmp_path: Path, monkeypatch):
    base_dir = tmp_path
    audio_dir = base_dir / "audio/forvo_no"
    audio_dir.mkdir(parents=True)
    temp_dir = base_dir / "tmp_dl"
    temp_dir.mkdir()

    def fake_scrape_query_with_timeout(query: str, **kwargs):
        return None, "timeout after 1s", True

    monkeypatch.setattr(downloader_module, "scrape_query_with_timeout", fake_scrape_query_with_timeout)
    mapping = mod.download_audio_map(
        queries={"bank"},
        temp_dir=temp_dir,
        audio_dir=audio_dir,
        headed=True,
        workers=1,
        base_dir=base_dir,
        query_timeout_sec=1,
    )
    assert mapping == {}


def test_main_returns_1_when_no_vocab_files(mod, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setattr(mod, "iter_vocab_files", lambda _pattern: [])
    assert mod.main() == 1


def test_pending_workflow_appends_rows_and_sets_null_when_unresolved(mod, tmp_path: Path, monkeypatch):
    base_dir = tmp_path
    vocab = base_dir / "vocab" / "food.tsv"
    vocab.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(
        vocab,
        [
            "lexical-category",
            "english",
            "norwegian",
            "pronunciation",
            "example_sentence",
            "audio_file",
        ],
        [
            ["noun", "bread", "et brød", "brod", "Jeg kjøper et brød.", "null"],
        ],
    )

    pending = base_dir / "tmp" / "pending.tsv"
    mod.write_pending_rows(
        pending,
        [
            {
                "target_tsv": "vocab/food.tsv",
                "lexical-category": "noun",
                "english": "egg",
                "norwegian": "et egg",
                "pronunciation": "egg",
                "example_sentence": "Jeg spiser et egg.",
                "audio_file": "",
            },
            {
                "target_tsv": "vocab/food.tsv",
                "lexical-category": "expression",
                "english": "thanks",
                "norwegian": "takk",
                "pronunciation": "takk",
                "example_sentence": "Takk for maten.",
                "audio_file": "",
            },
        ],
    )

    audio = base_dir / "audio" / "forvo_no" / "no_egg_1_001.mp3"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"egg")

    monkeypatch.chdir(base_dir)
    monkeypatch.setattr(
        mod,
        "download_audio_map",
        lambda **kwargs: {"egg": "audio/forvo_no/no_egg_1_001.mp3"},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--pending-file", str(pending)],
    )

    assert mod.main() == 0

    _headers, rows = read_tsv(vocab)
    assert len(rows) == 3
    assert rows[1]["english"] == "egg"
    assert rows[1]["audio_file"] == "audio/forvo_no/no_egg_1_001.mp3"
    assert rows[2]["english"] == "thanks"
    assert rows[2]["audio_file"] == "null"


def test_pending_workflow_can_create_new_target_file(mod, tmp_path: Path, monkeypatch):
    base_dir = tmp_path
    pending = base_dir / "tmp" / "pending.tsv"
    mod.write_pending_rows(
        pending,
        [
            {
                "target_tsv": "vocab/new_topic.tsv",
                "lexical-category": "noun",
                "english": "bank",
                "norwegian": "en bank",
                "pronunciation": "bank",
                "example_sentence": "Banken er åpen.",
                "audio_file": "",
            },
        ],
    )

    audio = base_dir / "audio" / "forvo_no" / "no_bank_1_001.mp3"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"bank")

    monkeypatch.chdir(base_dir)
    monkeypatch.setattr(
        mod,
        "download_audio_map",
        lambda **kwargs: {"bank": "audio/forvo_no/no_bank_1_001.mp3"},
    )
    monkeypatch.setattr(sys, "argv", ["prog", "--pending-file", str(pending)])

    assert mod.main() == 0
    new_vocab = base_dir / "vocab" / "new_topic.tsv"
    headers, rows = read_tsv(new_vocab)
    assert headers == [
        "lexical-category",
        "english",
        "norwegian",
        "pronunciation",
        "example_sentence",
        "audio_file",
    ]
    assert len(rows) == 1
    assert rows[0]["audio_file"] == "audio/forvo_no/no_bank_1_001.mp3"


def test_pending_workflow_defaults_headed_true_and_workers_one(mod, tmp_path: Path, monkeypatch):
    base_dir = tmp_path
    pending = base_dir / "tmp" / "pending.tsv"
    mod.write_pending_rows(
        pending,
        [
            {
                "target_tsv": "vocab/new_topic.tsv",
                "lexical-category": "noun",
                "english": "bank",
                "norwegian": "en bank",
                "pronunciation": "bank",
                "example_sentence": "Banken er åpen.",
                "audio_file": "",
            },
        ],
    )

    audio = base_dir / "audio" / "forvo_no" / "no_bank_1_001.mp3"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"bank")

    captured: dict[str, object] = {}

    def fake_download_audio_map(**kwargs):
        captured.update(kwargs)
        return {"bank": "audio/forvo_no/no_bank_1_001.mp3"}

    monkeypatch.chdir(base_dir)
    monkeypatch.setattr(mod, "download_audio_map", fake_download_audio_map)
    monkeypatch.setattr(sys, "argv", ["prog", "--pending-file", str(pending), "--workers", "4"])
    assert mod.main() == 0
    assert captured["headed"] is True
    assert captured["workers"] == 1


def test_pending_workflow_can_disable_headed(mod, tmp_path: Path, monkeypatch):
    base_dir = tmp_path
    pending = base_dir / "tmp" / "pending.tsv"
    mod.write_pending_rows(
        pending,
        [
            {
                "target_tsv": "vocab/new_topic.tsv",
                "lexical-category": "noun",
                "english": "bank",
                "norwegian": "en bank",
                "pronunciation": "bank",
                "example_sentence": "Banken er åpen.",
                "audio_file": "",
            },
        ],
    )

    audio = base_dir / "audio" / "forvo_no" / "no_bank_1_001.mp3"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"bank")

    captured: dict[str, object] = {}

    def fake_download_audio_map(**kwargs):
        captured.update(kwargs)
        return {"bank": "audio/forvo_no/no_bank_1_001.mp3"}

    monkeypatch.chdir(base_dir)
    monkeypatch.setattr(mod, "download_audio_map", fake_download_audio_map)
    monkeypatch.setattr(sys, "argv", ["prog", "--pending-file", str(pending), "--no-headed"])
    assert mod.main() == 0
    assert captured["headed"] is False
