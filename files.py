from typing import List

from common.api import ExtensionAPI
from common.llm import call_llm
from common.utils import parse_prompt, get_prompt_template
from extensions.default import build_context
from extensions.common.terminal import get_terminal_snapshot


def get_yaml(response) -> List[str]:
    """Extract YAML code blocks from markdown response.

    Args:
        response: String containing markdown response

    Returns:
        List of paths extracted from YAML code blocks in markdown
    """
    yaml_blocks = []
    lines = response.split('\n')
    in_yaml_block = False

    current_block = []

    for line in lines:
        if line.strip().startswith('```yaml'):
            in_yaml_block = True
            current_block = []
            continue
        elif line.strip().startswith('```') and in_yaml_block:
            in_yaml_block = False
            yaml_blocks.append('\n'.join(current_block))
            continue

        if in_yaml_block:
            current_block.append(line)

    return yaml_blocks


def extract_paths_from_yaml(yaml_blocks: List[str]) -> List[str]:
    paths = []
    for block in yaml_blocks:
        for line in block.split('\n'):
            line = line.split('#')[0]
            line = line.strip()
            if line.startswith('-'):
                path = line[1:].strip()
                paths.append(path)

    return paths


def extension(api: ExtensionAPI):
    """Main extension function that handles chat interactions with the AI assistant."""

    command, model, prompt = parse_prompt(api)

    api.push_meta(f'model: {model}, command: {command}')
    terminal_snapshot = get_terminal_snapshot(api)
    repo_paths = {f.path: f for f in api.repo_files}

    if command == 'context':
        api.log('Normal context')
        context = build_context(api,
                                other_files=api.opened_files,
                                selection=api.selection,
                                file_list=api.repo_files,
                                current_file=api.current_file,
                                terminal=terminal_snapshot,
                                cursor=(api.cursor_row, api.cursor_column),
                                )
        api.push_meta(f'With context: {len(context) :,},'
                      f' selection: {bool(api.selection)}')
        # api.log(context)
        messages = [
            {'role': 'system', 'content': get_prompt_template('files.list.system', model=model)},
            {'role': 'user', 'content': context},
            *[m.to_dict() for m in api.chat_history],
            {'role': 'user', 'content': f'Prompt:\n\n```\n{prompt}\n```'},
        ]
    else:
        raise ValueError(f'Unknown command: {command}')

    api.log(f'messages {len(messages)}')
    api.log(f'prompt {api.prompt}')
    # api.log(context)

    response = call_llm(api, model, messages)

    files = get_yaml(response)
    files = extract_paths_from_yaml(files)

    api.push_meta(f'Files:\n' + '\n'.join(files))

    files = [repo_paths[f] for f in files if f in repo_paths]
    bad = [f for f in files if not f.exists()]
    if bad:
        api.push_meta(
            f'The following files do not exist: {"".join(f"<code>{f.path}</code>" for f in bad)}')

    files = [f for f in files if f.exists()]
    context = build_context(api,
                                      other_files=files,
                                      selection=api.selection,
                                      file_list=files,
                                      current_file=api.current_file,
                                      terminal=terminal_snapshot,
                                      cursor=(api.cursor_row, api.cursor_column),
                                      )

    api.push_meta(f'With context: {len(context) :,},'
                  f' selection: {bool(api.selection)}')
    # api.log(context)
    messages = [
        {'role': 'system', 'content': get_prompt_template('files.system', model=model)},
        {'role': 'user', 'content': context},
        *[m.to_dict() for m in api.chat_history],
        {'role': 'user', 'content': prompt},
    ]

    call_llm(api, model, messages)