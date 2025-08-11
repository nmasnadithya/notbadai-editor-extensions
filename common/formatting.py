import typing

if typing.TYPE_CHECKING:
    from .api import File

FILE_TYPE = {
    '.py': 'python',
    '.ts': 'typescript',
    '.js': 'javascript',
}

LINE_COMMENT = {
    'python': '#',
    'typescript': '//',
}


def markdown_code_block(content: str, *, type_: str = '') -> str:
    return f"```{type_}\n{content}\n```"


def markdown_section(title: str, content: str) -> str:
    return f"## {title}\n\n{content.strip()}"  # test


def add_line_comment(file: 'File', line: str, comment: str) -> str:
    ft = FILE_TYPE.get(file.suffix(), '')
    cm = LINE_COMMENT.get(ft, '//')

    return line.rstrip() + f'  {cm} {comment.strip()}'