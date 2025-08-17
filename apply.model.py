import time
from typing import List, Dict

from openai import OpenAI

from common.api import ExtensionAPI
from common.diff import get_matches
from common.settings import LLM_PROVIDERS


def call_llm(api: ExtensionAPI, model: str, messages: List[Dict[str, str]], content: str):
    start_time = time.time()

    provider = None
    for p in LLM_PROVIDERS:
        if p['name'] == api.api_provider:
            provider = p
            break

    assert provider is not None

    client = OpenAI(api_key=api.api_key, base_url=provider['base_url'])

    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    merged_code = response.choices[0].message.content
    matches, cleaned_patch = get_matches(content, merged_code)

    api.apply_diff(cleaned_patch, matches)

    elapsed = time.time() - start_time
    meta_data = f'time: {elapsed:.2f}s'
    api.update_progress(100, f'apply completed {meta_data}')


def extension(api: ExtensionAPI):
    prompt = api.prompt.rstrip()  # no left strip for indentation

    if api.edit_file.path == api.current_file.path:
        content = api.current_file.get_content()
    else:
        try:
            content = api.edit_file.get_content()
        except FileNotFoundError:
            content = ''

    model = 'morph/morph-v3-fast'
    instruction = ''

    messages = [
        {
            "role": "user",
            "content": f"<instructions>{instruction}</instructions>\n<code>f{content}</code>\n<update>{prompt}</update>"
        }
    ]

    call_llm(api, model, messages, content)
