from common.api import ExtensionAPI
from common.llm import call_llm
from common.utils import extract_code_block


def extension(api: ExtensionAPI):
    api.notify('Generating inline completion...')

    # Get file content and cursor position
    lines = api.current_file.get_content().split('\n')
    current_line = lines[api.cursor_row - 1]

    # Get text before and after cursor
    text_before_cursor = current_line[:api.cursor_column - 1]

    # Get context: lines before current line + partial current line
    lines_before = lines[:api.cursor_row - 1]
    
    # Build context including the partial current line up to cursor
    if lines_before:
        context_before = '\n'.join(lines_before) + '\n' + text_before_cursor
    else:
        context_before = text_before_cursor

    # Get file extension for syntax highlighting
    file_extension = api.current_file.suffix().lstrip('.')

    prompt = f"""You are an intelligent code completion assistant. Complete the code at the cursor position.

## Context before current line:

{context_before}

## Current Line:

{text_before_cursor}

Please suggest a completion that would naturally fit at the cursor position. 

- It can be a single word, partial line, or multiple lines
- Make sure it's syntactically correct and contextually appropriate
- Wrap your response in triple backticks with the appropriate language identifier: ```{file_extension}
- Only provide the completion text within the code block, no explanations outside of it
- Do NOT repeat the text that's already before the cursor position
"""

    messages = [{'role': 'user', 'content': prompt}]

    api.log(prompt)

    model = 'mistralai/devstral-medium'
    api.start_chat()

    content = call_llm(api, model, messages)
    content = extract_code_block(content)
    
    if content.startswith(text_before_cursor):
        content = content[len(text_before_cursor):]

    # need to press tab to accept and esc to reject
    api.apply_inline_completion(content)