"""Bounded CSV and XLSX spreadsheet parsing with zip-bomb and formula guards."""

from __future__ import annotations

import csv
import io
import math
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

import openpyxl

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 2000
MAX_COLUMNS = 60
MAX_HEADER_ROW = 10
MAX_SCANNED_ROWS = 10_000
MAX_UNCOMPRESSED_BYTES = 30 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
_CHUNK_SIZE = 64 * 1024
_XML_DANGEROUS_MARKERS = (b"<!DOCTYPE", b"<!ENTITY")
_XLSX_MAGIC = b"PK\x03\x04"

SheetFormat = Literal["csv", "xlsx"]


class SheetFormatError(ValueError):
    """Raised when an uploaded spreadsheet violates format, size, or safety limits."""


@dataclass(frozen=True)
class SheetCell:
    text: str
    uncached_formula: bool = False


@dataclass(frozen=True)
class ParsedColumn:
    index: int
    key: str
    header: str
    raw_header: str


@dataclass(frozen=True)
class ParsedRow:
    row_number: int
    cells: dict[str, SheetCell]


@dataclass(frozen=True)
class ParsedSheet:
    format: SheetFormat
    sheets: list[str]
    selected_sheet: str | None
    detected_header_row: int
    header_row: int
    columns: list[ParsedColumn]
    rows: list[ParsedRow]


def _detect_format(data: bytes, filename: str | None) -> SheetFormat:
    lower_name = (filename or "").strip().lower()
    if lower_name.endswith(".xls"):
        raise SheetFormatError("Legacy .xls files are not supported; save as .xlsx or .csv")
    if lower_name.endswith(".xlsx"):
        if not data.startswith(_XLSX_MAGIC):
            raise SheetFormatError("Invalid XLSX workbook")
        return "xlsx"
    if data.startswith(_XLSX_MAGIC):
        return "xlsx"
    return "csv"


def _validate_xlsx_zip(data: bytes) -> None:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise SheetFormatError("Invalid XLSX workbook") from error
    with archive:
        declared_total = 0
        infos = archive.infolist()
        if not infos:
            raise SheetFormatError("Invalid XLSX workbook")
        for info in infos:
            if info.file_size < 0 or info.compress_size < 0:
                raise SheetFormatError("Invalid XLSX archive metadata")
            declared_total += info.file_size
            if declared_total > MAX_UNCOMPRESSED_BYTES:
                raise SheetFormatError("XLSX archive exceeds the 30 MiB uncompressed limit")
            if info.file_size > 0 and (
                info.compress_size == 0
                or info.file_size / info.compress_size > MAX_COMPRESSION_RATIO
            ):
                raise SheetFormatError("XLSX archive compression ratio exceeds the 100:1 limit")

        actual_total = 0
        for info in infos:
            if not info.filename.lower().endswith((".xml", ".rels")):
                continue
            member_read = 0
            tail = b""
            with archive.open(info, "r") as stream:
                while True:
                    chunk = stream.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    member_read += len(chunk)
                    actual_total += len(chunk)
                    if actual_total > MAX_UNCOMPRESSED_BYTES:
                        raise SheetFormatError("XLSX archive exceeds the 30 MiB uncompressed limit")
                    if member_read > info.file_size:
                        raise SheetFormatError("XLSX archive member size exceeds declared limit")
                    if info.compress_size > 0 and (
                        member_read / info.compress_size > MAX_COMPRESSION_RATIO
                    ):
                        raise SheetFormatError(
                            "XLSX archive compression ratio exceeds the 100:1 limit"
                        )
                    window = (tail + chunk).upper()
                    if any(marker in window for marker in _XML_DANGEROUS_MARKERS):
                        raise SheetFormatError(
                            "XLSX XML DTD and external entity declarations are not allowed"
                        )
                    tail = chunk[-32:]


def _format_xlsx_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        if value.is_integer():
            return str(int(value))
        return format(Decimal(str(value)).normalize(), "f")
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return str(int(value))
        return format(value.normalize(), "f")
    if isinstance(value, str):
        return value
    return str(value)


def _finalize_grid(
    *,
    fmt: SheetFormat,
    sheets: list[str],
    selected_sheet: str | None,
    raw_rows: list[tuple[int, list[SheetCell]]],
    header_row: int | None,
) -> ParsedSheet:
    if header_row is not None and not (1 <= header_row <= MAX_HEADER_ROW):
        raise SheetFormatError(f"Header row must be between 1 and {MAX_HEADER_ROW}")

    by_number = dict(raw_rows)
    detected_header_row: int | None = None
    for row_number in range(1, MAX_HEADER_ROW + 1):
        cells = by_number.get(row_number)
        if cells and any(cell.text.strip() or cell.uncached_formula for cell in cells):
            detected_header_row = row_number
            break
    if detected_header_row is None:
        raise SheetFormatError(f"No header row found in the first {MAX_HEADER_ROW} rows")

    effective_header_row = header_row if header_row is not None else detected_header_row
    header_cells = by_number.get(effective_header_row, [])
    if not any(cell.text.strip() for cell in header_cells):
        raise SheetFormatError(f"Header row {effective_header_row} is blank")

    data_raw: list[tuple[int, list[SheetCell]]] = []
    for row_number, cells in raw_rows:
        if row_number <= effective_header_row:
            continue
        if any(cell.text.strip() or cell.uncached_formula for cell in cells):
            data_raw.append((row_number, cells))
            if len(data_raw) > MAX_ROWS:
                raise SheetFormatError(f"Spreadsheet exceeds {MAX_ROWS} nonblank rows")

    if not data_raw:
        raise SheetFormatError("Spreadsheet contains no data rows")

    width = len(header_cells)
    for _, cells in data_raw:
        width = max(width, len(cells))

    # Trim trailing completely empty columns across header and data rows.
    while width > 0:
        col_idx = width - 1
        header_nonempty = col_idx < len(header_cells) and bool(header_cells[col_idx].text.strip())
        data_nonempty = any(
            col_idx < len(cells)
            and (bool(cells[col_idx].text.strip()) or cells[col_idx].uncached_formula)
            for _, cells in data_raw
        )
        if header_nonempty or data_nonempty:
            break
        width -= 1

    if width == 0:
        raise SheetFormatError(f"Header row {effective_header_row} is blank")
    if width > MAX_COLUMNS:
        raise SheetFormatError(f"Spreadsheet exceeds {MAX_COLUMNS} columns")

    columns: list[ParsedColumn] = []
    for index in range(width):
        raw_header = header_cells[index].text if index < len(header_cells) else ""
        trimmed = " ".join(raw_header.split())
        columns.append(
            ParsedColumn(
                index=index,
                key=f"col_{index}",
                header=trimmed or f"Column {index + 1}",
                raw_header=raw_header,
            )
        )

    parsed_rows: list[ParsedRow] = []
    for row_number, cells in data_raw:
        row_map: dict[str, SheetCell] = {}
        for column in columns:
            if column.index < len(cells):
                row_map[column.key] = cells[column.index]
            else:
                row_map[column.key] = SheetCell(text="")
        parsed_rows.append(ParsedRow(row_number=row_number, cells=row_map))

    return ParsedSheet(
        format=fmt,
        sheets=sheets,
        selected_sheet=selected_sheet,
        detected_header_row=detected_header_row,
        header_row=effective_header_row,
        columns=columns,
        rows=parsed_rows,
    )


def _parse_csv_sheet(data: bytes, header_row: int | None) -> ParsedSheet:
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise SheetFormatError("CSV must be UTF-8") from error
    raw_rows: list[tuple[int, list[SheetCell]]] = []
    nonblank_after_header_floor = 0
    try:
        reader = csv.reader(io.StringIO(content, newline=""), strict=True)
        for row_number, cells in enumerate(reader, start=1):
            if row_number > MAX_SCANNED_ROWS:
                raise SheetFormatError(f"Spreadsheet exceeds {MAX_SCANNED_ROWS} rows")
            if len(cells) > MAX_COLUMNS:
                # Allow trailing empty commas only if non-empty cells stay within MAX_COLUMNS.
                if any(cell.strip() for cell in cells[MAX_COLUMNS:]):
                    raise SheetFormatError(f"Spreadsheet exceeds {MAX_COLUMNS} columns")
                cells = cells[:MAX_COLUMNS]
            sheet_cells = [SheetCell(text=cell) for cell in cells]
            raw_rows.append((row_number, sheet_cells))
            if row_number > (header_row or 1) and any(cell.strip() for cell in cells):
                nonblank_after_header_floor += 1
                if nonblank_after_header_floor > MAX_ROWS + MAX_HEADER_ROW:
                    raise SheetFormatError(f"Spreadsheet exceeds {MAX_ROWS} nonblank rows")
    except csv.Error as error:
        raise SheetFormatError(f"Malformed CSV: {error}") from error
    return _finalize_grid(
        fmt="csv",
        sheets=[],
        selected_sheet=None,
        raw_rows=raw_rows,
        header_row=header_row,
    )


def _parse_xlsx_sheet(data: bytes, sheet_name: str | None, header_row: int | None) -> ParsedSheet:
    _validate_xlsx_zip(data)
    try:
        values_wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as error:
        raise SheetFormatError(f"Could not read XLSX workbook: {error}") from error

    try:
        sheets = list(values_wb.sheetnames)
        if not sheets:
            raise SheetFormatError("XLSX workbook contains no sheets")
        selected = sheet_name if sheet_name is not None else sheets[0]
        if selected not in sheets:
            raise SheetFormatError(f'Worksheet "{selected}" was not found')

        worksheet = values_wb[selected]
        value_rows: list[tuple[int, list[object]]] = []
        max_row_seen = 0
        max_col_seen = 0
        nonblank_count = 0

        for row_number, raw_tuple in enumerate(
            worksheet.iter_rows(min_row=1, max_col=MAX_COLUMNS + 1, values_only=True),
            start=1,
        ):
            if row_number > MAX_SCANNED_ROWS:
                raise SheetFormatError(f"Spreadsheet exceeds {MAX_SCANNED_ROWS} rows")
            if (
                len(raw_tuple) > MAX_COLUMNS
                and raw_tuple[MAX_COLUMNS] is not None
                and str(raw_tuple[MAX_COLUMNS]).strip()
            ):
                raise SheetFormatError(f"Spreadsheet exceeds {MAX_COLUMNS} columns")
            row_values = list(raw_tuple[:MAX_COLUMNS])
            max_row_seen = row_number
            row_last_nonempty = 0
            for idx, val in enumerate(row_values):
                if val is not None and (not isinstance(val, str) or val.strip()):
                    row_last_nonempty = idx + 1
            if row_last_nonempty > max_col_seen:
                max_col_seen = row_last_nonempty
            if row_last_nonempty > 0:
                nonblank_count += 1
                if nonblank_count > MAX_ROWS + MAX_HEADER_ROW:
                    raise SheetFormatError(f"Spreadsheet exceeds {MAX_ROWS} nonblank rows")
            value_rows.append((row_number, row_values))
    finally:
        values_wb.close()

    # Second bounded read-only pass (data_only=False) on the single selected sheet to detect
    # formula cells that have no cached value (which appear as None in data_only=True).
    formula_coords: set[tuple[int, int]] = set()
    if max_row_seen > 0:
        try:
            formula_wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=False)
        except Exception as error:
            raise SheetFormatError(f"Could not inspect XLSX formulas: {error}") from error
        try:
            formula_ws = formula_wb[selected]
            for row_number, cell_tuple in enumerate(
                formula_ws.iter_rows(
                    min_row=1,
                    max_row=max_row_seen,
                    max_col=MAX_COLUMNS + 1,
                    values_only=False,
                ),
                start=1,
            ):
                if len(cell_tuple) > MAX_COLUMNS:
                    extra = cell_tuple[MAX_COLUMNS]
                    if getattr(extra, "data_type", None) == "f" or (
                        extra.value is not None and str(extra.value).strip()
                    ):
                        raise SheetFormatError(f"Spreadsheet exceeds {MAX_COLUMNS} columns")
                for col_idx, cell in enumerate(cell_tuple[:MAX_COLUMNS]):
                    if getattr(cell, "data_type", None) == "f":
                        formula_coords.add((row_number, col_idx))
        finally:
            formula_wb.close()

    raw_rows: list[tuple[int, list[SheetCell]]] = []
    for row_number, row_values in value_rows:
        width = max(len(row_values), max_col_seen)
        # Include any column where an uncached formula appeared on this row.
        for f_row, f_col in formula_coords:
            if f_row == row_number and f_col + 1 > width:
                width = f_col + 1
        cells: list[SheetCell] = []
        for col_idx in range(width):
            val = row_values[col_idx] if col_idx < len(row_values) else None
            if val is None and (row_number, col_idx) in formula_coords:
                cells.append(SheetCell(text="", uncached_formula=True))
            else:
                cells.append(SheetCell(text=_format_xlsx_value(val)))
        raw_rows.append((row_number, cells))

    return _finalize_grid(
        fmt="xlsx",
        sheets=sheets,
        selected_sheet=selected,
        raw_rows=raw_rows,
        header_row=header_row,
    )


def parse_sheet(
    data: bytes,
    *,
    filename: str | None = None,
    sheet_name: str | None = None,
    header_row: int | None = None,
) -> ParsedSheet:
    if not data or len(data) > MAX_BYTES:
        raise SheetFormatError("Spreadsheet must be nonempty and at most 2 MiB")
    fmt = _detect_format(data, filename)
    if fmt == "xlsx":
        return _parse_xlsx_sheet(data, sheet_name=sheet_name, header_row=header_row)
    if sheet_name is not None:
        raise SheetFormatError("Worksheet selection applies only to XLSX files")
    return _parse_csv_sheet(data, header_row=header_row)
