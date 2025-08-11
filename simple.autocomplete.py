from typing import Tuple

from common.api import ExtensionAPI
from common.provider import AutoCompleteProvider


def get_cursor(content: str, row: int, column: int) -> Tuple[int, int]:
    lines = content.splitlines(keepends=True)

    if row > len(lines):
        line_from = len(content)
        cursor_pos = len(content)
    else:
        line_from = sum(len(lines[i]) for i in range(row - 1))
        cursor_pos = line_from + column - 1
        cursor_pos = min(cursor_pos, len(content))

    return line_from, cursor_pos


def extension(api: ExtensionAPI) -> None:
    line_from, cursor_pos = get_cursor(api.current_file.get_content(), api.cursor_row, api.cursor_column)

    data = {'current_content': api.current_file.get_content(),
            'current_path': api.current_file.path,
            'cursor_pos': cursor_pos,
            'line_number': api.cursor_row,
            'line_from': line_from,
            }

    provider = AutoCompleteProvider()

    res = provider.get_completions(data, api.current_file, api.opened_files)
    api.apply_autocomplete(res['suggestions'])
