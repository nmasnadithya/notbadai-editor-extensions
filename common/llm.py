import time
import typing
from typing import Dict, List

from openai import OpenAI

from .models import MODELS
from .settings import LLM_PROVIDERS

if typing.TYPE_CHECKING:
    from .api import ExtensionAPI


def call_llm(api: 'ExtensionAPI', model_id: str, messages: List[Dict[str, str]], *,
             push_to_chat: bool = True,
             temperature: float = 1.0,
             top_p: float = 1.0,
             n_outputs: int = 1,
             max_tokens: int = None,
             ):
    """Streams responses from the LLM and sends them to the chat UI in real-time."""

    model_info = MODELS[model_id]
    provider = None
    model_name = None
    for p in LLM_PROVIDERS:
        if p['name'] in model_info:
            model_name = model_info[p['name']]
            provider = p
            break

    start_time = time.time()

    client = OpenAI(api_key=provider['api_key'], base_url=provider['base_url'])
    # client = OpenAI(api_key=api.api_key, base_url="https://api.deepinfra.com/v1/openai")

    stream = client.chat.completions.create(
        model=model_name,
        messages=messages,
        stream=True,
        temperature=temperature,
        top_p=top_p,
        n=n_outputs,
        max_tokens=max_tokens,
    )

    thinking = False
    usage = None
    content = ''

    for chunk in stream:
        delta = chunk.choices[0].delta
        if push_to_chat:
            if getattr(delta, 'reasoning', None):
                if not thinking:
                    api.start_block('think')
                    thinking = True
                api.push_to_chat(content=delta.reasoning)

        if delta.content:
            if push_to_chat:
                if thinking:
                    api.end_block()
                    thinking = False
                api.push_to_chat(content=delta.content)
            content += delta.content

        if chunk.usage is not None:
            assert usage is None
            usage = chunk.usage

    elapsed = time.time() - start_time
    meta_data = f'Time: {elapsed:.2f}s'
    if usage is not None:
        api.log(str(usage))

        meta_data += f' Prompt tokens: {usage.prompt_tokens :,} Completion tokens {usage.completion_tokens :,}, Model: {model_name} @ {provider["name"]}'

    if push_to_chat:
        api.push_meta(meta_data.strip())

        api.terminate_chat()

    return content