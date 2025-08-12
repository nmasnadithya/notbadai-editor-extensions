import inspect
import json
import re
import typing
from pathlib import Path
from string import Template
from typing import Optional

if typing.TYPE_CHECKING:
    pass


def parse_prompt(api: 'ExtensionAPI') -> typing.Tuple[str, str, str]:
    prompt = api.prompt.strip()

    if prompt.startswith('@'):
        model = prompt.split()[0][1:]  # get text after @
        prompt = prompt[len(model) + 1:].strip()  # remove @model from prompt
    else:
        model = 'default'

    if prompt.startswith('\\'):
        command = prompt.split()[0][1:].strip()  # get text after \
        prompt = prompt[len(command) + 1:].strip()
    else:
        command = 'context'

    return command, model, prompt


def add_line_numbers(code: str) -> str:
    res = [str(idx + 1) + ": " + line.rstrip() for idx, line in enumerate(code.splitlines())]
    return '\n'.join(res)



def get_prompt_template(template_path: str, **kwargs) -> str:
    frame = inspect.stack()[1]
    # Get the file path of the caller
    caller_file = frame.filename

    path = Path(caller_file).parent / f'{template_path}.md'
    with open(str(path)) as f:
        template = Template(f.read())

    return template.substitute(kwargs)

def extract_code_block(text: str, language: Optional[str] = None, ignore_no_ticks=False) -> Optional[str]:
    if language:
        pattern = rf"```{re.escape(language)}\s*\n(.*?)```"
    else:
        pattern = r"```(?:\w+)?\s*\n(.*?)```"

    m = re.search(pattern, text, re.DOTALL)

    if m:
        return m.group(1)

    if ignore_no_ticks:
        return text
    else:
        return None


def parse_json(api: 'ExtensionAPI', response: str):
    try:
        return json.loads(response)
    except json.decoder.JSONDecodeError:
        block = extract_code_block(response)
        block = block.strip()
        if not block:
            raise ValueError("No JSON block detected in model response")
        try:
            return json.loads(block)
        except json.decoder.JSONDecodeError as e:
            api.log(block)
            raise e