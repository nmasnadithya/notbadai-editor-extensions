import json
import time
from typing import Dict, List, Tuple

from openai import OpenAI

from common.api import ExtensionAPI, File
from common.models import MODELS
from common.settings import LLM_PROVIDERS
from common.formatting import markdown_section, markdown_code_block, add_line_comment
from common.terminal import get_terminal_snapshot
from common.utils import parse_prompt, get_prompt_template


def search_repo_files(api: ExtensionAPI, query: str, file_extensions: List[str] = None) -> List[Dict]:
    """Search for a query string across all repository files.

    Args:
        api: ExtensionAPI instance to access repo files
        query: The string to search for
        file_extensions: Optional list of file extensions to limit search (e.g., ['.py', '.js'])

    Returns:
        List of dictionaries containing file path, line number, and line content
    """
    results = []

    for file in api.repo_files:
        # Filter by file extensions if specified
        if file_extensions:
            if not any(file.path.endswith(ext) for ext in file_extensions):
                continue

        try:
            content = file.get_content()
            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                if query.lower() in line.lower():
                    results.append({
                        "file_path": file.path,
                        "line_number": line_num,
                        "content": line.strip()
                    })
        except Exception as e:
            # Skip files that can't be read
            continue

    api.push_meta('<strong>Search Results</strong><br/>' +
                  json.dumps(results, indent=4))

    return results


def read_file(api: ExtensionAPI, file_path: str) -> str:
    """Read the content of a file from the repository.

    Args:
        api: ExtensionAPI instance to access repo files
        file_path: Path to the file to read

    Returns:
        String content of the file
    """
    try:
        # Find the file in repo_files
        for file in api.repo_files:
            if file.path == file_path:
                return file.get_content()
        # If not found in repo_files, try to read directly
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"


def get_function_by_name(name):
    if name == "search_repo_files":
        return search_repo_files
    elif name == "read_file":
        return read_file


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_repo_files",
            "description": "Search for a query string across all repository files and return matching lines with file paths and line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The string to search for in the repository files",
                    },
                    "file_extensions": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Optional list of file extensions to limit search (e.g., ['.py', '.js'])",
                    },
                },
                "required": ["api", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the content of a file from the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read",
                    },
                },
                "required": ["api", "file_path"],
            },
        },
    },
]

tools = TOOLS


def call_llm(
        api: 'ExtensionAPI',
        model_id: str,
        messages,
        *,
        push_to_chat: bool = True,
        temperature: float = 1.0,
        top_p: float = 1.0,
        n_outputs: int = 1,
        max_tokens: int = None,
):
    """Streams responses from the LLM and sends them to the chat UI in real-time."""

    model_info = MODELS[model_id]

    if len(api.api_keys.keys) == 0:
        raise ValueError('API key required. Configure at least one in Extensions → Management.')

    api_key, model_name = None, None
    if api.api_keys.default.provider in model_info:
        model_name = model_info[api.api_keys.default.provider]
        api_key = api.api_keys.default
    else:
        for k in api.api_keys.keys:
            if k.provider in model_info:
                model_name = model_info[k.provider]
                api_key = k
                break

    if api_key is None:
        raise ValueError(f"The API provider does not support {model_id} model")

    provider = None
    for p in LLM_PROVIDERS:
        if p['name'] == api_key.provider:
            provider = p
            break

    start_time = time.time()

    client = OpenAI(api_key=api_key.key, base_url=provider["base_url"])
    # client = OpenAI(api_key=api.api_key, base_url="https://api.deepinfra.com/v1/openai")

    stream = client.chat.completions.create(
        model=model_name,
        messages=messages,
        tools=tools,
        stream=True,
        temperature=temperature,
        top_p=top_p,
        n=n_outputs,
        max_tokens=max_tokens,
    )

    thinking = False
    usage = None
    content = ""
    response = []
    # Buffer for a tool/function call (partial) if one is in progress
    in_tool_call = False
    tool_call_buf = []

    for chunk in stream:
        choice = chunk.choices[0]
        delta = choice.delta
        if push_to_chat:
            if getattr(delta, "reasoning", None):
                if not thinking:
                    api.start_block("think")
                    thinking = True
                api.push_to_chat(content=delta.reasoning)

        # If there is content
        if hasattr(delta, "content") and delta.content:
            # If currently inside a tool_call, we probably shouldn't push normal content yet
            if in_tool_call:
                # The model is (per spec) not supposed to give normal content during a function_call streaming
                # But if it does, you can buffer or handle gracefully. Here, we'll treat as error / flush.
                content += delta.content
            else:
                # Normal assistant content
                if push_to_chat:
                    if thinking:
                        api.end_block()
                        thinking = False
                    api.push_to_chat(content=delta.content)
                content += delta.content

        if delta.tool_calls:
            # Mark that we are in function call mode
            in_tool_call = True

            for tool_call in delta.tool_calls:
                tool_index = tool_call.index
                while len(tool_call_buf) < tool_index + 1:
                    tool_call_buf.append({
                        "id": tool_call.id,
                        "name": "",
                        "arguments": ""
                    })
                # Append parts
                if tool_call.function.name:
                    tool_call_buf[tool_index]["name"] += tool_call.function.name
                if tool_call.function.arguments:
                    tool_call_buf[tool_index]["arguments"] += tool_call.function.arguments

        # Check if this chunk ends a tool/function call
        finish_reason = getattr(choice, "finish_reason", None)
        if in_tool_call and finish_reason == "tool_calls":
            # We got the full tool call name + arguments
            # First, flush any pending assistant content
            if content.strip():
                response.append({
                    "role": "assistant",
                    "content": content,
                })
            content = ''
            tool_calls = [ {
                "id": tool_call["id"],
                "function": {
                    "name": tool_call["name"],
                    "arguments": tool_call["arguments"]
                },
                # optionally: id or other metadata if available
            } for tool_call in tool_call_buf if tool_call["name"] or tool_call["arguments"]]

            # Push metadata / logging / meta UI
            for tool_call in tool_calls:
                try:
                    args_dict = json.loads(tool_call["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args_dict = {}
                api.log(f"Tool call: {tool_call["function"]['name']} args {args_dict}")
                api.push_meta(f'<strong>{tool_call["function"]["name"]}</strong>(' +
                              ', '.join(f'{k}={repr(v)}' for k, v in args_dict.items()) + ')')

            response.append({
                'role': 'assistant',
                'tool_calls':tool_calls,
            })

            # Reset buffers
            in_tool_call = False
            tool_call_buf = []

        if chunk.usage is not None:
            assert usage is None
            usage = chunk.usage

    elapsed = time.time() - start_time
    meta_data = f"Time: {elapsed:.2f}s"
    if usage is not None:
        api.log(str(usage))

        meta_data += f' Prompt tokens: {usage.prompt_tokens :,} Completion tokens {usage.completion_tokens :,}, Model: {model_name} @ {provider["name"]}'

    if push_to_chat:
        api.push_meta(meta_data.strip())

        api.terminate_chat()

    if not content.strip():
        response.append({
            "role": "assistant",
            "content": content,
        })

    return response

def build_context(api: 'ExtensionAPI', *,
                  current_file: File,
                  open_files: List['File'] = None,
                  selection: str = None,
                  terminal: str = None,
                  cursor: Tuple[int, int] = None,
                  file_list: List['File'] = None,
                  git_diff: str = None,
                  ) -> str:
    """Builds the context string from the current file and selection."""
    context = []

    if file_list:
        repo_files = [f'{f.path}`' for f in file_list]
        context.append(markdown_section("List of Files", "\n".join(repo_files)))

    if open_files:
        open_files = [f'{f.path}`' for f in open_files]
        context.append(markdown_section("Opened files", "\n\n".join(open_files)))

    if current_file:
        api.push_meta(f'Current file: {current_file.path}')
        context.append(
            markdown_section("Current File",
                             f"Path: `{current_file.path}`\n\n" +
                             markdown_code_block(current_file.get_content()))
        )

    # Add git diff to context
    if git_diff is not None:
        context.append(
            markdown_section("Recent Git Changes",
                             f"Git diff showing recent changes:\n\n" +
                             markdown_code_block(git_diff, type_="diff"))
        )

    if terminal:
        if len(terminal) > 40_000:
            pre_text = f'Terminal output is {len(terminal)} chars long, and here is the last 40k chars of it.\n\n'
        else:
            pre_text = f'Terminal output is {len(terminal)} chars long.'

        context.append(
            markdown_section("Terminal output",
                             f"{pre_text}\n\n" + markdown_code_block(terminal[-40000:]))
        )

    if selection and selection.strip():
        context.append(
            markdown_section("Selection",
                             "This is the code snippet that I'm referring to\n\n" +
                             markdown_code_block(selection))
        )

    if cursor:
        block = current_file.get_content().split('\n')
        assert len(block) > cursor[0], f'Cursor row {cursor[0]} block of length {len(block)}'
        prefix = block[cursor[0] - 3: cursor[0]]
        line = block[cursor[0]]
        line = add_line_comment(current_file, line, f'Cursor is here: `{line[:cursor[1]].strip()}`')
        suffix = block[cursor[0] + 1:cursor[0] + 4]

        block = prefix + [line] + suffix

        context.append(markdown_section("Cursor position",
                                        markdown_code_block('\n'.join(block))))

    return "\n\n".join(context)



def extension(api: ExtensionAPI):
    """Main extension function that handles chat interactions with the AI assistant."""

    command, model, prompt = parse_prompt(api)

    api.push_meta(f'model: {model}, command: {command}')
    terminal_snapshot = get_terminal_snapshot(api)
    repo_paths = {f.path: f for f in api.repo_files}

    if command == 'context':
        api.log('Normal context')
        context = build_context(api,
                                open_files=[],
                                selection=api.selection,
                                file_list=api.repo_files,
                                current_file=api.current_file,
                                terminal=terminal_snapshot,
                                cursor=(api.cursor_row - 1, api.cursor_column - 1),
                                )
        api.push_meta(f'With context: {len(context) :,},'
                      f' selection: {bool(api.selection)}')
        # api.log(context)
        messages = [
            {'role': 'system', 'content': get_prompt_template('tools.system', model=model)},
            {'role': 'user', 'content': context},
            *[m.to_dict() for m in api.chat_history],
            {'role': 'user', 'content': prompt},
        ]
    else:
        raise ValueError(f'Unknown command: {command}')

    api.log(f'messages {len(messages)}')
    api.log(f'prompt {api.prompt}')
    # api.log(context)

    while True:
        res = call_llm(api, model, messages)
        api.log('#' * 20 + 'Call')
        has_calls = False
        for r in res:
            messages.append(r)
        for r in res:
            if 'tool_calls' in r:
                has_calls = True
                # Handle tool calls
                tool_calls = r['tool_calls']
                tool_results = []

                # Execute each tool call
                for tool_call in tool_calls:
                    function_name = tool_call['function']['name']
                    function_args = json.loads(tool_call['function']['arguments'])

                    # Get the function and execute it
                    function = get_function_by_name(function_name)
                    if function:
                        result = function(api, **function_args)
                        tool_results.append({
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(result),
                            "tool_call_id": tool_call['id']
                        })

                # Add tool results to messages and call LLM again to get final response
                messages.extend(tool_results)  # Add tool results
        if not has_calls:
            break
