from __future__ import annotations

import multiprocessing as mp
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from scrape_forvo import scrape

from .audio_naming import query_from_forvo_filename
from .audio_paths import normalize_audio_path, resolve_audio_path


def scrape_query(query: str, temp_dir: Path, headed: bool) -> Path | None:
    result = scrape(
        query,
        outdir=str(temp_dir),
        lang="no",
        use_playwright=True,
        headed=headed,
    )
    if result.downloaded_count <= 0:
        return None

    candidates = [candidate for candidate in result.candidates if candidate.out_path]
    if not candidates:
        return None

    out_path = Path(candidates[0].out_path)
    return out_path if out_path.exists() else None


def _scrape_query_worker(query: str, temp_dir: str, headed: bool, queue: mp.Queue) -> None:
    try:
        downloaded = scrape_query(query, temp_dir=Path(temp_dir), headed=headed)
        queue.put({"path": str(downloaded) if downloaded else "", "error": ""})
    except Exception as exc:  # noqa: BLE001
        queue.put({"path": "", "error": str(exc)})


def scrape_query_with_timeout(
    query: str,
    *,
    temp_dir: Path,
    headed: bool,
    timeout_sec: int,
) -> tuple[Path | None, str | None, bool]:
    context = mp.get_context("spawn")
    queue: mp.Queue = context.Queue()
    process = context.Process(target=_scrape_query_worker, args=(query, str(temp_dir), headed, queue))
    process.start()
    process.join(timeout=max(1, timeout_sec))

    if process.is_alive():
        process.terminate()
        process.join()
        return None, f"timeout after {timeout_sec}s", True

    result = queue.get() if not queue.empty() else {}
    error = result.get("error", "") if isinstance(result, dict) else ""
    path_str = result.get("path", "") if isinstance(result, dict) else ""
    if error:
        return None, error, False
    if not path_str:
        return None, None, False

    out_path = Path(path_str)
    return (out_path if out_path.exists() else None), None, False


def hydrate_from_existing_files(audio_dir: Path, mapping: dict[str, str], *, base_dir: Path) -> None:
    for path in sorted(audio_dir.glob("no_*.mp3")):
        label = query_from_forvo_filename(path.name)
        if label and label not in mapping:
            mapping[label] = normalize_audio_path(path, base_dir=base_dir)


def collect_pending_queries(
    queries: set[str],
    mapping: dict[str, str],
    *,
    base_dir: Path,
) -> tuple[list[tuple[int, str]], int]:
    query_list = sorted(queries)
    total = len(query_list)
    pending: list[tuple[int, str]] = []

    for idx, query in enumerate(query_list, start=1):
        existing = mapping.get(query.casefold())
        if existing and resolve_audio_path(existing, base_dir=base_dir).exists():
            print(f"[{idx}/{total}] reuse: {query} -> {existing}")
            continue
        pending.append((idx, query))

    return pending, total


def download_audio_map(
    queries: set[str],
    temp_dir: Path,
    audio_dir: Path,
    headed: bool,
    workers: int,
    base_dir: Path,
    query_timeout_sec: int = 45,
    initial_map: dict[str, str] | None = None,
) -> dict[str, str]:
    temp_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    mapping: dict[str, str] = dict(initial_map or {})
    hydrate_from_existing_files(audio_dir, mapping, base_dir=base_dir)
    pending, total = collect_pending_queries(queries, mapping, base_dir=base_dir)

    if not pending:
        return mapping

    def run_one(query: str) -> tuple[str, Path | None, str | None, bool]:
        try:
            downloaded, err, timed_out = scrape_query_with_timeout(
                query,
                temp_dir=temp_dir,
                headed=headed,
                timeout_sec=query_timeout_sec,
            )
            return query, downloaded, err, timed_out
        except Exception as exc:  # noqa: BLE001
            return query, None, str(exc), False

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(run_one, query): (idx, query) for idx, query in pending}
        for future in as_completed(futures):
            idx, query = futures[future]
            qkey = query.casefold()
            _, downloaded, err, timed_out = future.result()
            if err:
                if timed_out:
                    print(f"[{idx}/{total}] timeout: {query}: {err}")
                    continue
                print(f"[{idx}/{total}] failed: {query}: {err}")
                continue

            if not downloaded:
                print(f"[{idx}/{total}] no-download: {query}")
                continue

            target = audio_dir / downloaded.name
            if target.resolve() != downloaded.resolve():
                shutil.move(str(downloaded), str(target))
            mapping[qkey] = normalize_audio_path(target, base_dir=base_dir)
            print(f"[{idx}/{total}] saved: {query} -> {mapping[qkey]}")

    return mapping
