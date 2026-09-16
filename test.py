from __future__ import annotations

import argparse
import io
import sys
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout


BAR_WIDTH = 36


class CompactProgressResult(unittest.TestResult):
    def __init__(self, *, total: int, failfast: bool = False):
        super().__init__()
        self.total = max(0, int(total))
        self.failfast = failfast
        self.completed = 0
        self.started_at = time.perf_counter()
        self._last_line_length = 0

    def startTest(self, test):
        super().startTest(test)

    def stopTest(self, test):
        super().stopTest(test)
        self.completed += 1
        self._render_progress()

    def addSuccess(self, test):
        super().addSuccess(test)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        if self.failfast:
            self.stop()

    def addError(self, test, err):
        super().addError(test, err)
        if self.failfast:
            self.stop()

    def addSkip(self, test, reason):
        super().addSkip(test, reason)

    def _render_progress(self):
        total = self.total or 1
        ratio = min(1.0, self.completed / total)
        filled = int(round(BAR_WIDTH * ratio))
        bar = "█" * filled + "░" * (BAR_WIDTH - filled)
        percent = int(round(ratio * 100))
        elapsed = time.perf_counter() - self.started_at

        line = (
            f"[{bar}] {percent:3d}%  "
            f"{self.completed}/{self.total}  "
            f"{elapsed:5.1f}s"
        )
        padding = " " * max(0, self._last_line_length - len(line))
        print(f"\r{line}{padding}", end="", flush=True)
        self._last_line_length = len(line)

    def finish_progress(self):
        if self.total == 0:
            print("[------------------------------------]   0%  0/0")
        else:
            print()


def _short_test_name(test) -> str:
    try:
        return test.id()
    except Exception:
        return str(test)


def _print_problem_section(title: str, entries):
    if not entries:
        return

    print(f"\n{title}")
    print("-" * len(title))
    for index, (test, traceback_text) in enumerate(entries, start=1):
        print(f"{index}. {_short_test_name(test)}")
        lines = [line for line in str(traceback_text).rstrip().splitlines() if line.strip()]
        # Default tetap ringkas: tampilkan bagian akhir traceback yang biasanya
        # berisi lokasi error + exception/assertion terpenting.
        for line in lines[-12:]:
            print(f"   {line}")


def run_tests(*, failfast: bool = False, show_captured: bool = False) -> int:
    loader = unittest.TestLoader()
    suite = loader.discover("tests")
    total = suite.countTestCases()

    print("=" * 58)
    print(" TAX CONVERTER L-1 — TEST RUNNER")
    print("=" * 58)
    print(f"Menjalankan {total} test...\n")

    result = CompactProgressResult(total=total, failfast=failfast)
    captured_out = io.StringIO()
    captured_err = io.StringIO()

    started = time.perf_counter()
    if show_captured:
        suite.run(result)
    else:
        with redirect_stdout(captured_out), redirect_stderr(captured_err):
            suite.run(result)

    # Progress ditulis ke stdout. Karena redirect di atas juga menangkapnya,
    # render satu status final setelah redirect selesai.
    if not show_captured:
        result._render_progress()
    result.finish_progress()

    elapsed = time.perf_counter() - started
    passed = (
        result.testsRun
        - len(result.failures)
        - len(result.errors)
        - len(result.skipped)
        - len(result.expectedFailures)
        - len(result.unexpectedSuccesses)
    )

    print()
    print("=" * 58)
    if result.wasSuccessful():
        print(" PASS — SEMUA TEST HIJAU")
    else:
        print(" FAIL — ADA TEST YANG PERLU DIPERBAIKI")
    print("=" * 58)
    print(f"PASS    : {passed}")
    print(f"FAIL    : {len(result.failures)}")
    print(f"ERROR   : {len(result.errors)}")
    print(f"SKIP    : {len(result.skipped)}")
    print(f"TOTAL   : {result.testsRun}/{total}")
    print(f"TIME    : {elapsed:.2f}s")

    _print_problem_section("FAILURES", result.failures)
    _print_problem_section("ERRORS", result.errors)

    if result.unexpectedSuccesses:
        print("\nUNEXPECTED SUCCESS")
        print("------------------")
        for test in result.unexpectedSuccesses:
            print(f"- {_short_test_name(test)}")

    if show_captured:
        return 0 if result.wasSuccessful() else 1

    # Output dari test biasanya dibuang agar terminal bersih. Kalau run gagal,
    # tampilkan sedikit output tambahan hanya bila memang ada.
    extra = (captured_err.getvalue() + "\n" + captured_out.getvalue()).strip()
    if not result.wasSuccessful() and extra:
        lines = extra.splitlines()
        print("\nOUTPUT TAMBAHAN (bagian akhir)")
        print("-----------------------------")
        for line in lines[-20:]:
            print(line)

    return 0 if result.wasSuccessful() else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compact test runner untuk Tax Converter L-1."
    )
    parser.add_argument(
        "-x",
        "--failfast",
        action="store_true",
        help="Berhenti setelah failure/error pertama.",
    )
    parser.add_argument(
        "-v",
        "--show-output",
        action="store_true",
        help="Jangan sembunyikan stdout/stderr dari test.",
    )
    args = parser.parse_args()
    return run_tests(
        failfast=args.failfast,
        show_captured=args.show_output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
