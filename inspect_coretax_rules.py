from pathlib import Path
import pandas as pd


FOLDER = Path(r"D:\Coretax_Export")


CATEGORY_SHEETS = [
    "KAS SETARA KAS",
    "PIUTANG",
    "INVESTASI",
    "HARTA BERGERAK",
    "HARTA TIDAK BERGERAK",
    "LAINNYA",
]


def clean(value):
    if value is None:
        return ""

    text = str(value).strip()

    if text.lower() == "nan":
        return ""

    return " ".join(text.split())


def inspect_category(file_path, sheet_name):
    print()
    print("=" * 90)
    print(f"FILE     : {file_path.name}")
    print(f"KATEGORI : {sheet_name}")
    print("=" * 90)

    try:
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=0,
            dtype=object,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return

    # Normalisasi nama kolom
    columns = [clean(c) for c in df.columns]

    print()
    print("COLUMNS:")
    for i, col in enumerate(columns, 1):
        print(f"  {i}. {col}")

    # Cari kolom berdasarkan nama
    def find_column(*names):
        for name in names:
            name = name.lower()

            for index, col in enumerate(columns):
                if col.lower() == name:
                    return index

        return None

    excel_idx = find_column(
        "Kolom pada excel"
    )

    xml_idx = find_column(
        "Kolom pada xml"
    )

    instruction_idx = find_column(
        "Petunjuk pengisian"
    )

    example_idx = find_column(
        "Contoh Pengisian",
        "Contoh pengisian",
    )

    validation_idx = find_column(
        "Validasi"
    )

    note_idx = find_column(
        "Keterangan",
        "Keterangan tambahan",
    )

    if excel_idx is None:
        print()
        print(
            "WARNING: kolom 'Kolom pada excel' "
            "tidak ditemukan."
        )
        return

    print()
    print("FIELD RULES")
    print("-" * 90)

    field_count = 0

    for row_index in range(len(df)):
        excel_name = clean(
            df.iloc[row_index, excel_idx]
        )

        # Lewati baris kosong
        if not excel_name:
            continue

        # Lewati baris header kedua jika ada
        if excel_name.lower() in {
            "kolom pada excel",
            "code",
        }:
            continue

        field_count += 1

        xml_name = (
            clean(df.iloc[row_index, xml_idx])
            if xml_idx is not None
            else ""
        )

        instruction = (
            clean(
                df.iloc[
                    row_index,
                    instruction_idx,
                ]
            )
            if instruction_idx is not None
            else ""
        )

        example = (
            clean(
                df.iloc[
                    row_index,
                    example_idx,
                ]
            )
            if example_idx is not None
            else ""
        )

        validation = (
            clean(
                df.iloc[
                    row_index,
                    validation_idx,
                ]
            )
            if validation_idx is not None
            else ""
        )

        note = (
            clean(
                df.iloc[
                    row_index,
                    note_idx,
                ]
            )
            if note_idx is not None
            else ""
        )

        print()
        print(f"{field_count}. {excel_name}")

        if xml_name:
            print(f"   XML        : {xml_name}")

        if example:
            print(f"   CONTOH     : {example}")

        if validation:
            print(f"   VALIDASI   : {validation}")

        if instruction:
            print(f"   PETUNJUK   : {instruction}")

        if note:
            print(f"   KETERANGAN : {note}")

    print()
    print(f"TOTAL FIELD : {field_count}")


def inspect_file(file_path):
    try:
        excel = pd.ExcelFile(file_path)
    except Exception as exc:
        print(
            f"\nERROR membaca {file_path.name}: {exc}"
        )
        return

    for sheet_name in CATEGORY_SHEETS:
        if sheet_name in excel.sheet_names:
            inspect_category(
                file_path,
                sheet_name,
            )


def main():
    print("=" * 90)
    print("CORETAX FIELD RULE INSPECTOR")
    print("=" * 90)

    print(f"Folder: {FOLDER}")

    if not FOLDER.exists():
        print("Folder tidak ditemukan.")
        return

    files = sorted(
        [
            p
            for p in FOLDER.iterdir()
            if p.is_file()
            and p.suffix.lower() == ".xlsx"
        ],
        key=lambda p: p.name.lower(),
    )

    print(
        f"Excel files ditemukan: {len(files)}"
    )

    for file_path in files:
        inspect_file(file_path)

    print()
    print("=" * 90)
    print("SELESAI")
    print("=" * 90)


if __name__ == "__main__":
    main()