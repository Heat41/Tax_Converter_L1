from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd


SUPPORTED_EXTENSIONS = {".xlsx", ".xls"}


def clean_value(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()

    if text.lower() == "nan":
        return ""

    return text


def clean_header(value: Any) -> str:
    text = clean_value(value)
    text = text.replace("\n", " ")
    text = " ".join(text.split())
    return text


def find_header_row(df: pd.DataFrame) -> int | None:
    """
    Mencari kandidat baris header.
    Hanya memeriksa 20 baris pertama.
    """

    limit = min(len(df), 20)

    for row_index in range(limit):
        row = df.iloc[row_index]

        non_empty = sum(
            1
            for value in row
            if clean_value(value)
        )

        # Header biasanya memiliki minimal 2 kolom terisi.
        if non_empty >= 2:
            return row_index

    return None


def is_sensitive(header: str) -> bool:
    h = header.lower()

    keywords = [
        "npwp",
        "nik",
        "nama",
        "alamat",
        "telepon",
        "telp",
        "phone",
        "email",
        "rekening",
    ]

    return any(keyword in h for keyword in keywords)


def sample_value(value: Any, header: str) -> str:
    text = clean_value(value)

    if not text:
        return ""

    if is_sensitive(header):
        if len(text) <= 4:
            return "***"

        if len(text) <= 8:
            return text[:2] + "***"

        return text[:3] + "***" + text[-2:]

    # Batasi panjang contoh agar output tetap pendek.
    if len(text) > 30:
        return text[:27] + "..."

    return text


def inspect_sheet(
    excel_path: Path,
    sheet_name: str,
) -> None:

    try:
        df = pd.read_excel(
            excel_path,
            sheet_name=sheet_name,
            header=None,
            dtype=object,
        )
    except Exception as exc:
        print(f"  ERROR: {type(exc).__name__}: {exc}")
        return

    raw_rows, raw_columns = df.shape

    print(f"  Sheet       : {sheet_name}")
    print(
        f"  Raw size    : {raw_rows} rows x "
        f"{raw_columns} columns"
    )

    if raw_rows == 0 or raw_columns == 0:
        print("  Status      : EMPTY")
        return

    header_row = find_header_row(df)

    if header_row is None:
        print("  Header      : tidak ditemukan")
        return

    print(
        f"  Header row  : {header_row + 1}"
    )

    # Ambil header.
    headers = [
        clean_header(value)
        for value in df.iloc[header_row].tolist()
    ]

    # Buang kolom kosong di bagian paling kanan.
    while headers and not headers[-1]:
        headers.pop()

    print(
        f"  Columns     : {len(headers)}"
    )

    # Header kosong.
    empty_headers = [
        str(i + 1)
        for i, header in enumerate(headers)
        if not header
    ]

    if empty_headers:
        print(
            "  Empty hdr   : "
            + ", ".join(empty_headers)
        )
    else:
        print("  Empty hdr   : none")

    # Duplicate headers.
    normalized = [
        header.lower()
        for header in headers
        if header
    ]

    duplicates = sorted(
        {
            header
            for header in normalized
            if normalized.count(header) > 1
        }
    )

    if duplicates:
        print(
            "  Dup hdr     : "
            + ", ".join(duplicates)
        )
    else:
        print("  Dup hdr     : none")

    # Tampilkan semua header.
    print("  Headers     :")

    for index, header in enumerate(headers, start=1):
        print(
            f"    {index:>2}. "
            f"{header or '<EMPTY>'}"
        )

    # Data setelah header.
    data = df.iloc[
        header_row + 1:,
        :len(headers),
    ].copy()

    if data.empty:
        print("  Data rows   : 0")
        return

    # Buang baris kosong.
    mask = data.apply(
        lambda row: any(
            clean_value(value)
            for value in row
        ),
        axis=1,
    )

    data = data.loc[mask].reset_index(drop=True)

    print(
        f"  Data rows   : {len(data)}"
    )

    # Kolom profiling singkat.
    print("  Profile     :")

    for index, header in enumerate(headers):
        if index >= data.shape[1]:
            continue

        column = data.iloc[:, index]

        non_empty_values = [
            value
            for value in column.tolist()
            if clean_value(value)
        ]

        empty_count = len(data) - len(
            non_empty_values
        )

        dtype = str(column.dtype)

        examples = [
            sample_value(value, header)
            for value in non_empty_values[:2]
        ]

        example_text = " | ".join(
            example
            for example in examples
            if example
        )

        print(
            f"    - {header or '<EMPTY>'}: "
            f"type={dtype}, "
            f"empty={empty_count}, "
            f"contoh={example_text}"
        )

    # Dua baris contoh saja.
    print("  Samples     :")

    sample_count = min(2, len(data))

    for row_index in range(sample_count):
        values = []

        for column_index, header in enumerate(headers):
            value = data.iloc[
                row_index,
                column_index,
            ]

            text = sample_value(
                value,
                header,
            )

            values.append(
                f"{header or '?'}={text}"
            )

        print(
            "    "
            + " | ".join(values)
        )


def inspect_file(excel_path: Path) -> None:

    print()
    print("=" * 80)
    print(f"FILE: {excel_path.name}")
    print("=" * 80)

    try:
        excel = pd.ExcelFile(excel_path)

        print(
            f"Extension   : "
            f"{excel_path.suffix.lower()}"
        )

        print(
            f"Size        : "
            f"{excel_path.stat().st_size:,} bytes"
        )

        print(
            f"Sheets      : "
            f"{len(excel.sheet_names)}"
        )

        for sheet_name in excel.sheet_names:
            inspect_sheet(
                excel_path,
                sheet_name,
            )

    except Exception as exc:
        print(
            f"ERROR: {type(exc).__name__}: {exc}"
        )


def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Inspect struktur export Coretax "
            "secara ringkas."
        )
    )

    parser.add_argument(
        "folder",
        nargs="?",
        default=".",
        help="Folder berisi file Coretax.",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help=(
            "Mode ringkas. "
            "Parameter ini tersedia untuk kompatibilitas."
        ),
    )

    args = parser.parse_args()

    folder = Path(
        args.folder
    ).expanduser().resolve()

    print("=" * 80)
    print("CORETAX EXPORT INSPECTOR - SUMMARY")
    print("=" * 80)
    print(f"Folder: {folder}")

    if not folder.exists():
        print(
            f"ERROR: folder tidak ditemukan: "
            f"{folder}"
        )
        raise SystemExit(1)

    if not folder.is_dir():
        print(
            f"ERROR: bukan folder: {folder}"
        )
        raise SystemExit(1)

    files = sorted(
        [
            path
            for path in folder.iterdir()
            if path.is_file()
            and path.suffix.lower()
            in SUPPORTED_EXTENSIONS
        ],
        key=lambda path: path.name.lower(),
    )

    print(
        f"Excel files: {len(files)}"
    )

    if not files:
        print(
            "Tidak ditemukan file .xlsx atau .xls."
        )
        return

    for excel_path in files:
        inspect_file(excel_path)

    print()
    print("=" * 80)
    print("SELESAI")
    print("=" * 80)
    print("Read-only: file Excel tidak diubah.")
    print("Database: tidak disentuh.")


if __name__ == "__main__":
    main()