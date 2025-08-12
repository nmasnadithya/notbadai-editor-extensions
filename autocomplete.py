import json
import re
import time
from typing import List, Dict, Any

from common.api import ExtensionAPI
from common.llm import call_llm
from common.utils import extract_code_block

MAX_PREDICTIONS = 4

SYSTEM_PROMPT = """
You are an expert programmer assisting a colleague in adding code to an existing file.

Your colleague will give you:
• The surrounding code (context)  
• Clear instructions describing the snippet to add

Your task:
• Provide exactly 4 different suggestions for the next line of code
• Match the file's indentation, style, and conventions
• Do *not* include explanations or comments

You MUST respond with valid JSON in this EXACT format:
{
  "suggestions": [
    "first code line suggestion",
    "second code line suggestion", 
    "third code line suggestion",
    "fourth code line suggestion"
  ]
}

Each suggestion should be a complete, valid line of code. No markdown, no backticks, no extra formatting.
""".strip()

COUNTER = 0


def _get_last_word(prefix: str):
    """Split context to identify the current identifier being completed."""
    pattern = r'([A-Za-z_][A-Za-z0-9_]*\s*|[A-Za-z_][A-Za-z0-9_]*\.)$'
    match = re.search(pattern, prefix)

    ctx = match.group(0) if match else ''
    # rest = prefix[:-len(ctx)] if ctx else prefix

    return ctx


class AutocompleteExtension:
    def __init__(self, api: ExtensionAPI):
        self.api = api
        self.lines = api.current_file.get_content().splitlines()
        self.row = api.cursor_row - 1
        self.column = api.cursor_column - 1
        self.other_files = api.opened_files
        self.current_file = api.current_file
        self.line = self.lines[self.row]
        self.line_prefix = self.line[:self.column]
        self.last_word = _get_last_word(self.line_prefix)

        self.api.log(f'Initialize {len(self.lines)} lines,'
                     f' cursor at row {self.row}, column {self.column}'
                     f' current prefix: `{self.line_prefix}`'
                     f' last word: `{self.last_word}`'
                     f' line {self.line}')

    def build_prompt(self) -> List[Dict[str, str]]:
        """Build the prompt for the language model based on code context."""
        prefix = '\n'.join(self.lines[:self.row])
        suffix = '\n'.join(self.lines[self.row + 1:])

        user_content = ''
        file_type = 'python'  # TODO

        if self.other_files:
            user_content += "First, I'll provide context on the other files relevant to this task, "
            user_content += "followed by content of the file I'm currently editing. "
            user_content += "Then, I will show you the insertion point and give you the instruction.\n\n"

            user_content += "## Relevant Files\n\n"
            for f in self.other_files:
                assert f.path != self.current_file.path
                user_content += f'### `{f.path}`\n\n'
                user_content += f'```{file_type}\n{f.get_content()}\n```\n\n'

            user_content += f"\n\n## Current File\n\n"
            user_content += f"### `{self.current_file.path}`\n\n```{file_type}\n"
        else:
            user_content += "First, I will give you the code I'm working on.\n"
            user_content += "Then, I will show you the insertion point and give you the instruction.\n\n"

            user_content += f"## Code\n\n```{file_type}\n"

        user_content += prefix + "\n# INSERT_YOUR_NEXT_LINE\n"

        if suffix.strip():
            user_content += f'{suffix}\n'

        user_content += "```\n\n"
        user_content += "## Instructions\n\n"
        user_content += f"Provide exactly 4 different suggestions for what `INSERT_YOUR_NEXT_LINE` should be. "
        user_content += "Return your response as JSON with a 'suggestions' array containing 4 strings.\n"
        user_content += "Avoid repeating any lines in the vicinity of the current one (e.g., those directly before or after).\n"

        if self.line_prefix.strip():
            user_content += f'\nThe next line begins with `{self.line_prefix}`.'

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]


    def get_completions(self) -> List[Dict[str, Any]]:
        """Get completions for the current cursor position."""

        start_time = time.time()
        messages = self.build_prompt()

        response_text = call_llm(self.api, 'devstral', messages,
                                 push_to_chat=False,
                                 max_tokens=512,
                                 temperature=0.8,
                                 top_p=0.8,
                                 )

        try:
            # Clean up response - remove any markdown code blocks if present
            data = json.loads(extract_code_block(response_text, ignore_no_ticks=True).strip())
            suggestions = [str(s).strip() for s in data['suggestions']]
        except (json.JSONDecodeError, KeyError, TypeError, TypeError) as e:
            self.api.log(f"Failed to parse response as JSON: {e}")
            self.api.log(f"Raw response: {response_text}")
            suggestions = []

        time_elapsed = int((time.time() - start_time) * 1000)

        self.api.log(f"suggestions: {suggestions}")

        completions = []
        seen = set()

        for s in suggestions:
            if not s.lstrip().startswith(self.line_prefix.lstrip()):
                continue

            s = s.lstrip()[len(self.line_prefix.lstrip()):]

            if not s.strip():
                continue

            if s.strip() in seen:
                continue

            seen.add(s.strip())

            label = self.last_word + s

            completions.append({'label': label, 'text': self.line_prefix + s})

        self.api.log(f'{time_elapsed}: Found {completions}')

        return completions[:MAX_PREDICTIONS]


def extension(api: ExtensionAPI) -> None:
    """Main extension entry point."""
    global COUNTER
    COUNTER += 1

    api.log(f'{COUNTER}: Autocomplete extension started')

    # Create extension instance and get completions
    autocomplete_ext = AutocompleteExtension(api)
    api.log(f'"{autocomplete_ext.line_prefix}"')
    # api.apply_autocomplete([{'label': autocomplete_ext.last_word + 'YY', 'text': autocomplete_ext.line_prefix + 'YY'}])
    # return
    suggestions = autocomplete_ext.get_completions()

    api.apply_autocomplete(suggestions)