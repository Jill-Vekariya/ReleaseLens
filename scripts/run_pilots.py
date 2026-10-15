"""Run fixed tuning comparisons plus load, memory and cache-size observations.

No heldout labels are used. CPU time/power and download bandwidth are not a dollar bill.
"""

import ctypes
import hashlib
import json
import os
import platform
from pathlib import Path
from time import perf_counter

from releaselens.benchmark import run
from releaselens.retrieval import configured_embedder

ROOT = Path(__file__).resolve().parents[1]


def peak_rss_bytes():
    if os.name == "nt":
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t)
                for name in (
                    "PeakWorkingSetSize",
                    "WorkingSetSize",
                    "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage",
                    "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage",
                    "PagefileUsage",
                    "PeakPagefileUsage",
                )
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Counters),
            wintypes.DWORD,
        ]
        if not psapi.GetProcessMemoryInfo(
            kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.PeakWorkingSetSize
    import resource

    multiplier = 1 if platform.system() == "Darwin" else 1024
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * multiplier


def main():
    start = perf_counter()
    encoder = configured_embedder()
    loaded_ms = (perf_counter() - start) * 1000
    learned = run(ROOT / "evaluation/pilot-learned-tuning.json", encoder)
    # Same machine/process, questions, labels, settings and source chunks. Hash is a test double.
    baseline = run(ROOT / "evaluation/pilot-hash-tuning.json")
    cache = Path(os.environ.get("HF_HOME", ROOT / ".model-cache"))
    probe = "ReleaseLens reproducible encoding request_timeout 30 seconds."
    first, second = encoder.encode(probe), encoder.encode(probe)
    assert max(abs(a - b) for a, b in zip(first, second, strict=True)) < 1e-6
    model_files = {}
    for folder in cache.glob("hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/*"):
        for p in folder.rglob("*"):
            if p.is_file():
                model_files[str(p.relative_to(folder))] = {
                    "bytes": p.stat().st_size,
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                }
    record = {
        "encoder": encoder.name,
        "device": "cpu",
        "max_sequence_length": encoder.model.max_seq_length,
        "normalization": "L2; inputs longer than model token limit truncate",
        "repeat_probe_max_abs_difference": max(
            abs(a - b) for a, b in zip(first, second, strict=True)
        ),
        "model_snapshot_files": model_files,
        "model_load_ms_including_download_if_uncached": loaded_ms,
        "peak_process_resident_bytes": peak_rss_bytes(),
        "memory_scope": "Whole process high-water mark including Python, model, indexes and both pilot runs; not model-only memory",
        "model_cache_bytes": sum(p.stat().st_size for p in cache.rglob("*") if p.is_file()),
        "python": platform.python_version(),
        "os": platform.platform(),
        "cpu_logical_count": os.cpu_count(),
        "learned_dataset_sha256": learned["dataset_sha256"],
        "hash_dataset_sha256": baseline["dataset_sha256"],
        "provider_cost_usd": 0,
        "electricity_and_network_cost": "Not metered; no paid service or API invoked",
    }
    assert record["learned_dataset_sha256"] == record["hash_dataset_sha256"]
    (ROOT / "evaluation/retrieval-resources.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
