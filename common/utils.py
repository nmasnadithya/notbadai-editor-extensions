import re
import typing
from typing import Optional

if typing.TYPE_CHECKING:
    from .api import ExtensionAPI


def parse_prompt(api: 'ExtensionAPI') -> typing.Tuple[str, str, str]:
    from .models import get_model_name
    prompt = api.prompt.strip()

    if prompt.startswith('@'):
        model_key = prompt.split()[0][1:]  # get text after @
        model = get_model_name(model_key)
        prompt = prompt[len(model_key) + 1:].strip()  # remove @model from prompt
    else:
        model = get_model_name('default')

    if prompt.startswith('\\'):
        command = prompt.split()[0][1:].strip()  # get text after \
        prompt = prompt[len(command) + 1:].strip()
    else:
        command = 'context'

    return command, model, prompt


def add_line_numbers(code: str) -> str:
    res = ''
    for idx, line in enumerate(code.split('\n')):
        res += str(idx + 1) + ": " + line + '\n'
    return res
    
    
def extract_code_block(text: str, language: str | None = None) -> Optional[str]:
    if language:
        pattern = rf"```{re.escape(language)}\s*\n(.*?)```"
    else:
        pattern = r"```(?:\w+)?\s*\n(.*?)```"

    m = re.search(pattern, text, re.DOTALL)
    
    return m.group(1) if m else None