"""
run_tests.py — Chạy toàn bộ test suite và in báo cáo chi tiết.

Cách dùng:
    python tests/run_tests.py              # chạy tất cả
    python tests/run_tests.py -v           # verbose
    python tests/run_tests.py --fast       # chỉ unit tests (không cần mạng)
    python tests/run_tests.py test_02      # chỉ chạy module cụ thể
"""
from __future__ import annotations

import os
import sys
import time
import argparse
import unittest
import importlib

# Chạy từ thư mục gốc project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TESTS_DIR = os.path.join(BASE_DIR, "tests")

# Tất cả module tests (theo thứ tự)
ALL_MODULES = [
    # tests.test_02_task_queue removed — task_queue.py was dead code (INC-03)
    "tests.test_03_sheet_client",
    "tests.test_04_drive_downloader",
    "tests.test_05_misc_utils",
    "tests.test_06_concurrent_runner",
    "tests.test_07_k1_metadata",
    "tests.test_08_k5_notifier",
    "tests.test_09_k6_retry",
    "tests.test_10_k8_reels",
    "tests.test_11_upgrades",
    "tests.test_12_tiktok",
]

COLORS = {
    "green":  "\033[92m",
    "red":    "\033[91m",
    "yellow": "\033[93m",
    "cyan":   "\033[96m",
    "bold":   "\033[1m",
    "reset":  "\033[0m",
}

def col(text: str, color: str) -> str:
    if sys.platform == "win32":
        return text  # Windows terminal may not support ANSI
    return f"{COLORS.get(color,'')}{text}{COLORS['reset']}"


def print_header():
    print()
    print("=" * 65)
    print("  BOT UP FACEBOOK — Test Suite")
    print(f"  Python {sys.version.split()[0]}   |   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    print()


def run_module(module_name: str, verbosity: int = 1) -> unittest.TestResult:
    try:
        mod = importlib.import_module(module_name)
    except ImportError as e:
        print(f"  [SKIP] {module_name}: Import error — {e}")
        result = unittest.TestResult()
        result.errors.append((None, str(e)))
        return result

    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(mod)
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        # Open devnull with utf-8 so Unicode in error messages doesn't crash on Windows
        stream=open(os.devnull, "w", encoding="utf-8") if verbosity == 0 else sys.stdout,
    )
    return runner.run(suite)


def print_module_summary(module_name: str, result: unittest.TestResult, elapsed: float):
    short = module_name.split(".")[-1]
    total  = result.testsRun
    failed = len(result.failures)
    errors = len(result.errors)
    skipped = len(getattr(result, "skipped", []))
    passed = total - failed - errors - skipped

    status = "PASS" if failed == 0 and errors == 0 else "FAIL"
    bar = "✓" if status == "PASS" else "✗"

    print(f"  {bar}  {short:<35}  "
          f"passed={passed:>2}  failed={failed:>2}  error={errors:>2}  "
          f"skip={skipped:>2}  [{elapsed:.2f}s]")


def print_grand_total(all_results: list[tuple[str, unittest.TestResult, float]]):
    total_run = total_failed = total_errors = total_skipped = 0
    total_time = 0.0
    for _, r, t in all_results:
        total_run     += r.testsRun
        total_failed  += len(r.failures)
        total_errors  += len(r.errors)
        total_skipped += len(getattr(r, "skipped", []))
        total_time    += t

    passed = total_run - total_failed - total_errors - total_skipped
    ok = total_failed == 0 and total_errors == 0

    print()
    print("=" * 65)
    verdict = "PASSED" if ok else "FAILED"
    print(f"  {verdict}   "
          f"Total: {total_run}  |  "
          f"Passed: {passed}  |  "
          f"Failed: {total_failed}  |  "
          f"Error: {total_errors}  |  "
          f"Skip: {total_skipped}  |  "
          f"Time: {total_time:.2f}s")
    print("=" * 65)

    if not ok:
        print()
        print("  FAILURE DETAILS:")
        for mod_name, r, _ in all_results:
            for test_case, tb in r.failures + r.errors:
                print(f"\n  [{mod_name}] {test_case}")
                # In 5 dòng cuối của traceback
                lines = tb.strip().split("\n")
                for line in lines[-5:]:
                    print(f"    {line}")
    print()
    return ok


def main():
    parser = argparse.ArgumentParser(description="Bot UP Facebook Test Runner")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("filter", nargs="?", default="",
                        help="Filter: tên module hoặc class/method (e.g. test_02, TestTaskQueue)")
    args = parser.parse_args()

    verbosity = 2 if args.verbose else 0
    filt = args.filter.lower()

    modules = [m for m in ALL_MODULES if not filt or filt in m.lower()]
    if not modules:
        print(f"Không tìm thấy module nào khớp với '{args.filter}'")
        sys.exit(1)

    print_header()
    print(f"  Chạy {len(modules)} module(s):")
    for m in modules:
        print(f"    • {m.split('.')[-1]}")
    print()

    all_results: list[tuple[str, unittest.TestResult, float]] = []

    for mod_name in modules:
        t0 = time.time()
        if args.verbose:
            print(f"\n{'─'*65}")
            print(f"  {mod_name}")
            print('─'*65)
        result = run_module(mod_name, verbosity=verbosity)
        elapsed = time.time() - t0
        all_results.append((mod_name, result, elapsed))
        if not args.verbose:
            print_module_summary(mod_name, result, elapsed)

    ok = print_grand_total(all_results)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
