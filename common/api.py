import requests
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

TAGS = {
    'think': 'collapse',
    'meta': 'metadata'
}


class ToolState:
    """Represents the state of a UI component in a tool interface."""

    def __init__(self, tool_type: str, name: str, value: str = None, disabled: bool = False):
        self.type = tool_type
        self.name = name
        self.value = value or ""
        self.disabled = disabled


class ToolComponent:
    """Base class for tool UI components."""

    def __init__(self, component_type: str, **kwargs):
        self.type = component_type
        self.kwargs = kwargs

    def to_data(self):
        """Convert component to dictionary format for serialization."""
        data = {'type': self.type}
        data.update(self.kwargs)
        return data


class Button(ToolComponent):
    def __init__(self, name: str, disabled: bool = False):
        super().__init__('button', name=name, disabled=disabled)


class Input(ToolComponent):
    def __init__(self, name: str, placeholder: str = None, value: str = None, disabled: bool = False):
        super().__init__('input', name=name, placeholder=placeholder, value=value, disabled=disabled)


class File:
    def __init__(self, path: str, repo_path: str, content: str = None):
        self.path: str = path
        self._fs_path = Path(f'{repo_path}/{path}')
        self._content = content

    def suffix(self) -> str:
        return self._fs_path.suffix

    def exists(self) -> bool:
        return self._fs_path.is_file()

    def get_content(self) -> str:
        if self._content is not None:
            return self._content

        with open(self._fs_path, 'r') as f:
            self._content = f.read()
        return self._content


class Message:
    def __init__(self, **kwargs):
        self.role: str = kwargs["role"]
        self.content: str = kwargs["content"]

    def to_dict(self) -> Dict[str, str]:
        return {'role': self.role, 'content': self.content}


class ExtensionAPI:
    """Main API class that provides access to editor state and operations.

    Attributes:
            repo_files: List of all files in the repository
            repo_path: Path to the repository root
            current_file: Currently focused file
            edit_file: File being edited (for patch operations)
            opened_files: List of currently opened files
            selection: Currently selected text (if any)
            cursor_row: Current cursor row position
            cursor_column: Current cursor column position
            chat_history: List of previous chat messages
            terminal_snapshot: what user sees in the terminal screen
            terminal_before_reset: Terminal content from before last reset/clear
            context_files: Dictionary mapping user-specified paths to their corresponding file lists
            prompt: Current user prompt
            symbol: Symbol name (for symbol lookup)
            api_key: str
            api_provider: str
    """
    _meta_data: Any
    repo_files: List[File]
    repo_path: str
    current_file: Optional[File]
    opened_files: List[File]
    edit_file: Optional[File]
    selection: Optional[str]
    cursor_row: Optional[int]
    cursor_column: Optional[int]
    chat_history: List[Message]
    terminal_snapshot: Optional[List[str]]
    terminal_before_reset: Optional[List[str]]
    active_terminal_name: Optional[str]
    terminal_names: Optional[List[str]]
    context_files: Dict[str, List[File]]
    prompt: Optional[str]
    symbol: Optional[str]
    api_key: Optional[str]
    api_provider: Optional[str]
    audio_blob_path: Optional[str]
    tool_action: Optional[str]
    tool_state: Optional[Dict[str, ToolState]]

    _blocks: List[str]

    def load(self, **kwargs):
        self._meta_data = kwargs['meta_data']
        self.selection = kwargs.get('selection', None)
        self.cursor_row = kwargs.get('cursor_row', None)
        self.cursor_column = kwargs.get('cursor_column', None)
        self.prompt = kwargs.get('prompt', None)
        self.terminal_snapshot = kwargs.get('terminal_snapshot', None)
        self.terminal_before_reset = kwargs.get('terminal_before_reset', None)
        self.api_key = kwargs.get('api_key', None)
        self.api_provider = kwargs.get('api_provider', None)
        self.audio_blob_path = kwargs.get('audio_blob_path', None)
        self.tool_action = kwargs.get('tool_action', None)
        self.active_terminal_name = kwargs.get('active_terminal_name', None)
        self.terminal_names = kwargs.get('terminal_names', None)

        self.tool_state = {}
        if kwargs.get('tool_state', None):
            self.tool_state = kwargs['tool_state']
            for k, v in kwargs['tool_state'].items():
                self.tool_state[k] = ToolState(**v)

        if 'chat_history' in kwargs:
            self.chat_history = [Message(**m) for m in kwargs['chat_history']]
        else:
            self.chat_history = []

        self.symbol = kwargs.get('symbol', None)

        self.repo_path = kwargs['repo_path']
        current_file_content = kwargs.get('current_file_content', None)
        if kwargs['current_file'] is not None:
            self.current_file = File(kwargs['current_file'], self.repo_path, current_file_content)
        else:
            self.current_file = None
        self.repo_files = [File(p, self.repo_path) for p in kwargs['repo']]
        self.opened_files = [File(p, self.repo_path) for p in kwargs['opened_files']]

        self.edit_file = File(kwargs['edit_file'], self.repo_path) if 'edit_file' in kwargs else None

        context_files = {}
        for entry, values in kwargs.get('context_files', {}).items():
            files = [File(p, self.repo_path) for p in values]
            context_files[entry] = files
        self.context_files = context_files

        self._blocks = []

        return self

    def _dump(self, method: str, **kwargs):
        assert 'method' not in kwargs
        kwargs['method'] = method
        kwargs['meta_data'] = self._meta_data

        port = self._meta_data['port']
        requests.post(f'http://localhost:{port}/api/extension', json=kwargs)

    def get_terminal_data(self, terminal_name: str) -> Dict[str, List[str]]:
        """Get terminal data (snapshot and lines before reset) for a specific terminal.

        Args:
            terminal_name: Name of the terminal to get data from

        Returns:
            Dictionary with 'snapshot' and 'linesBeforeReset' keys containing lists of strings
        """
        port = self._meta_data['port']
        response = requests.get(f'http://localhost:{port}/api/terminal/{terminal_name}')
        response.raise_for_status()

        result = response.json()
        return result['data']

    def push_to_chat(self, content: str):
        """Send content to be displayed in the chat UI."""
        self._dump('push_chat', content=content)

    def start_block(self, type_: str):
        """Start a block of type `type`. `type_` can be `meta` or `think`."""

        tag = TAGS[type_]

        self.push_to_chat(f"\n<{tag}>")
        self._blocks.append(tag)

    def end_block(self):
        """
        End the current block
        """
        assert len(self._blocks) > 0

        tag = self._blocks.pop(-1)

        self.push_to_chat(f'</{tag}>\n')

    def push_block(self, type_: str, content: str):
        """
        Send a block of type `type`. `type_` can be `meta` or `think`
        """
        self.start_block(type_)
        self.push_to_chat(content)
        self.end_block()

    def push_meta(self, content: str):
        """
        Send a meta block.
        """
        self.start_block('meta')
        self.push_to_chat(content)
        self.end_block()

    def apply_autocomplete(self, suggestions: List[Dict[str, str]]):
        """Send autocomplete result to the client UI,
               should be a list of dict objects where each dict has two keys:
               label (string), and text (str)."""

        self._dump('apply_autocomplete', suggestions=suggestions)

    def apply_diff(self, patch: List[str], matches: List[List[int]], cursor_row: int = None, cursor_column: int = None):
        """
        Stream diff-match coordinates to the client UI.

        Args:
            patch: Lines of code in the patch to apply
            matches: list of [row_in_a, row_in_b] pairs returned by
                     extensions.extension_api.diff_lines.get_matches
            cursor_row: Optional row position (1-based) where to place the cursor after applying the diff
            cursor_column: Optional column position (1-based) where to place the cursor after applying the diff
        """
        self._dump('apply_diff', patch=patch, matches=matches, cursor_row=cursor_row, cursor_column=cursor_column)

    def send_diagnostics(self, diagnostics: List[Dict[str, Union[int, str]]]):
        """Send diagnostics result to the client UI,
        should be a list of dict objects where each dict has two keys:
        line_number (int), and description (str)."""

        self._dump('send_diagnostics', diagnostics=diagnostics)

    def send_inspector_results(self, results: List[Dict[str, Union[int, str]]]):
        """Send inspector result to the client UI,
        should be a list of dict objects where each dict has two keys:
        line_number (int), file_path (str), and description (str)."""

        self._dump('send_inspector_results', results=results)

    def send_symbol_results(self, intent: str, results: List[Dict]):
        """
        Send symbol analysis results (navigation or usage).

        Args:
            intent: Either "navigation" or "usage"
            results: List of dictionaries with file_path, line_number, excerpt
        """
        self._dump('send_symbol_results', intent=intent, results=results)

    def apply_inline_completion(self, text: str, cursor_row: int = None, cursor_column: int = None):
        """Apply inline completion suggestion at the current cursor position.

        This method displays ghost text that can be accepted with Tab or dismissed with Escape.
        The completion appears as grayed-out text at the specified position or current cursor location.

        Args:
            text: The completion text to display as ghost text
            cursor_row: Optional row position (1-based) where the completion should be applied.
                       If not provided, uses the current cursor row position
            cursor_column: Optional column position (1-based) where the completion should be applied.
                           If not provided, uses the current cursor column position
        """
        self._dump('apply_inline_completion', content=text, cursor_row=cursor_row, cursor_column=cursor_column)

    def terminate_chat(self):
        """Terminate the current chat message."""
        self._dump('terminate_chat')

    def start_chat(self):
        """Start chat message"""
        self._dump('start_chat')

    def log(self, message: str):
        """Log a debug message, shows in browser console."""
        self._dump('log', content=message)

    def update_progress(self, progress: float, message: str):
        """Update the progress of the extension in the UI.

        Args:
            :param message: The update message content
            :param progress: Progress value between 0.0 and 100.0
        """
        self._dump('update_progress', progress=progress, content=message)

    def notify(self, content: str, title: str = None):
        """Display a notification in the UI.

        Args:
            content: The notification message content
            title: Optional title for the notification
        """
        self._dump('notify', content=content, title=title)

    def send_audio_transcription(self, content: str):
        """Send audio transcription result to the client UI.

        Args:
            content: The transcribed text from audio input
        """
        self._dump('send_audio_transcription', content=content)

    def send_tool_interface(self, title: str, tool_interface: List[List[ToolComponent]]):
        """Send a tool interface to be rendered in the UI.

        Args:
            tool_interface: List of rows, where each row is a list of ToolComponent objects
            :param title:
        """

        serialized_rows = []
        for row in tool_interface:
            serialized_row = [component.to_data() for component in row]
            serialized_rows.append(serialized_row)

        self._dump('send_tool_interface', tool_interface={'title': title, 'rows': serialized_rows})
