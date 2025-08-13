FILE_TYPE_MAP = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'javascript',
    '.tsx': 'typescript',
    '.java': 'java',
    '.c': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.h': 'c',
    '.hpp': 'cpp',
    '.cs': 'csharp',
    '.php': 'php',
    '.rb': 'ruby',
    '.go': 'go',
    '.rs': 'rust',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'zsh',
    '.fish': 'fish',
    '.html': 'html',
    '.htm': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sass': 'sass',
    '.less': 'less',
    '.json': 'json',
    '.xml': 'xml',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.ini': 'ini',
    '.cfg': 'ini',
    '.conf': 'conf',
    '.md': 'markdown',
    '.markdown': 'markdown',
    '.txt': 'text',
    '.sql': 'sql',
    '.r': 'r',
    '.R': 'r',
    '.m': 'matlab',
    '.pl': 'perl',
    '.lua': 'lua',
    '.vim': 'vim',
    '.dockerfile': 'dockerfile',
    '.makefile': 'makefile',
}


def get_file_type(file_path: str) -> str:
    """Determine file type based on file extension."""
    if not file_path:
        return 'unknown'

    # Handle special cases first
    filename = file_path.lower().split('/')[-1]
    if filename in ('dockerfile', 'makefile'):
        return filename

    # check for file extension
    if '.' in filename:
        ext = '.' + filename.split('.')[-1]
        return FILE_TYPE_MAP.get(ext, 'unknown')

    return 'unknown'