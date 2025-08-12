import re
import typing

if typing.TYPE_CHECKING:
    from .api import ExtensionAPI


def _strip_ansi(text):
    # ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    ansi_escape = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)


def _clean_carriage_return(text):
    """
    For terminal history

    Cleans terminal output containing carriage returns by removing overwritten lines.

    Args:
        text (str): Raw terminal output containing \r characters

    Returns:
        str: Cleaned text with overwritten lines removed
    """
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        # Split by carriage return and keep only the last segment
        segments = line.split('\r')
        line = []
        for s in segments:
            s = list(s)
            if len(line) > len(s):
                line[:len(s)] = s
            else:
                line = s

        line = ''.join(line)
        if segments:
            cleaned_lines.append(line.rstrip())

    return '\n'.join(cleaned_lines)

def _clean_empty_lines(text):
    lines = text.split('\n')

    while lines and lines[0].strip() == '':
        lines.pop(0)
    while lines and lines[-1].strip() == '':
        lines.pop()

    return '\n'.join(lines)

def get_terminal_snapshot(api: 'ExtensionAPI'):
    text = _strip_ansi('\n'.join(api.terminal_snapshot))
    return _clean_empty_lines(text)