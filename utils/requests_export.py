"""Utilities for exporting request data to Excel workbooks."""

from __future__ import annotations

from io import BytesIO
from typing import Any, Callable, Iterable, Sequence

from fastapi.responses import StreamingResponse
from openpyxl import Workbook

RowBuilder = Callable[[Any], Sequence[Any]]


def export_requests_workbook(
    rows: Iterable[Any],
    headers: Sequence[str],
    row_builder: RowBuilder,
    filename: str = "talepler.xlsx",
) -> StreamingResponse:
    """Create a StreamingResponse containing the request export workbook.

    Args:
        rows: Iterable of database rows that will be exported. Each row is passed to
            ``row_builder`` to create the Excel row content.
        headers: Column titles to be written as the first row of the workbook.
        row_builder: Callable that receives each row and returns a sequence of values
            representing a single Excel row.
        filename: Name of the exported file suggested to the client.

    Returns:
        A ``StreamingResponse`` containing the generated workbook.
    """

    wb = Workbook()
    ws = wb.active
    ws.append(list(headers))

    for row in rows:
        ws.append(list(row_builder(row)))

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    headers_dict = {
        "Content-Disposition": f"attachment; filename={filename}",
    }
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers_dict,
    )
