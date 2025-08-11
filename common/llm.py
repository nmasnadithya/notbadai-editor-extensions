import time
import typing
from typing import Dict, List

from openai import OpenAI
from .secrets import OPEN_ROUTER_TOKEN, OPEN_ROUTER_URL

if typing.TYPE_CHECKING:
    from .api import ExtensionAPI

def call_llm(api: 'ExtensionAPI', model: str, messages: List[Dict[str, str]]):
    """Streams responses from the LLM and sends them to the chat UI in real-time."""

    start_time = time.time()

    client = OpenAI(api_key=OPEN_ROUTER_TOKEN, base_url=OPEN_ROUTER_URL)

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        temperature=1,
        top_p=1,
        extra_body={
        "reasoning": {          
            "max_tokens": 1500 
        }
        }
    )

    thinking = False
    prompt_tokens = None
    content = ''

    for chunk in stream:
        delta = chunk.choices[0].delta
        if getattr(delta, 'reasoning', None):
            if not thinking:
                api.start_block('think')
                thinking = True
            api.push_to_chat(content=delta.reasoning)

        if delta.content:
            if thinking:
                api.end_block()
                thinking = False
            api.push_to_chat(content=delta.content)
            content += delta.content

        if chunk.usage is not None:
            prompt_tokens = chunk.usage.prompt_tokens

    elapsed = time.time() - start_time
    meta_data = f'time: {elapsed:.2f}s'
    if prompt_tokens is not None:
        meta_data += f' prompt: {prompt_tokens :,} model: {model}'

    api.push_meta(meta_data.strip())

    api.terminate_chat()

    return content