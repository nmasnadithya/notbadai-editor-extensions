import time
import requests
from typing import Tuple, Optional, List

from .api import File
from .instruct import get_multi_file_prompt, get_single_file_prompt, parse_response
from .secrets import OPEN_ROUTER_TOKEN

MODEL_NAME = 'mistralai/devstral-small'
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'


def get_suggestions(offset: int,
                    open_files: Optional[List['File']] = None,
                    current_file: 'File' = None,
                    ):
    start_time = time.time()

    suggestions, log_probs, cached_tokens, prompt_tokens = (
        _get_suggestions(
            offset=offset,
            open_files=open_files,
            current_file=current_file,
        )
    )

    time_elapsed = int((time.time() - start_time) * 1000)

    return {
        "suggestions": suggestions,
        "log_probs": log_probs,
        "time_elapsed": time_elapsed,
        "cached_tokens": cached_tokens,
        "prompt_tokens": prompt_tokens,
    }


def _get_suggestions(*,
                     offset: int,
                     open_files: Optional[List['File']] = None,
                     current_file: 'File' = None,
                     ) -> Tuple[List[str], List[float], int, int]:
    text = current_file.get_content()

    # Get chat messages instead of formatted prompt
    if open_files is None or len(open_files) == 0:
        messages = get_single_file_prompt(text[:offset], text[offset:])
    else:
        file_context = ''
        for open_doc in open_files:
            if open_doc.path == current_file.path:
                continue
            file_context += '# ' + open_doc.path + '\n\n'
            file_context += open_doc.get_content() + '\n\n'
        messages = get_multi_file_prompt(text[:offset], text[offset:], file_context, current_file.path)

    # openRouter API request format
    headers = {
        'Authorization': f'Bearer {OPEN_ROUTER_TOKEN}',
        'Content-Type': 'application/json'
    }

    data = {
        'model': MODEL_NAME,
        'messages': messages,
        'temperature': 0.7,
        'max_tokens': 512,
        'stop': None
    }

    response = requests.post(OPENROUTER_URL, headers=headers, json=data)
    results = response.json()

    response_text = results['choices'][0]['message']['content'].strip()

    # parse the JSON response to get all 4 suggestions
    suggestions = parse_response(response_text)

    # Create dummy log_probs since OpenRouter doesn't always provide them
    log_probs = [-1.0] * len(suggestions)

    prompt_tokens = results.get('usage', {}).get('prompt_tokens', 0)
    cached_tokens = 0  # Not available from OpenRouter

    return suggestions, log_probs, cached_tokens, prompt_tokens
