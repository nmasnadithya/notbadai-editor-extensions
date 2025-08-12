import yaml
from typing import List, Dict

from openai import OpenAI

from common.api import ExtensionAPI
from common.utils import add_line_numbers, extract_code_block
from common.secrets import OPEN_ROUTER_TOKEN, OPEN_ROUTER_URL


def get_system_prompt() -> str:
    return """
You are an expert Python code analyzer. Your task is to analyze the provided code and determine whether the user wants to:
1. NAVIGATE to the definition of a symbol (find where it's defined)
2. FIND USAGES of a symbol (find all places where it's used)

Then provide the appropriate results.

Key decision factors:
- If the symbol appears to be at its definition site, user likely wants to find usages
- If the symbol appears to be at a usage site, user likely wants to navigate to definition
- Consider the context and what would be most helpful

For NAVIGATION (finding definition):
- Return only ONE result - the location where the symbol is defined
- Use intent: "navigation"

For USAGE FINDING (finding all usages):
- Return ALL locations where the symbol is used (not defined)
- Use intent: "usage"

Always include line excerpts for context.
""".strip()


def get_prompt(code: str, symbol: str, symbol_line_no: int, file_context: str = None, current_path: str = None) -> str:
    if file_context is None:
        # Single file scenario
        return f"""
# Python file with line numbers

****```python
{add_line_numbers(code)}
****```

# Symbol Analysis Request

name: {symbol}
current_line: {symbol_line_no}

# Instructions

1. First, determine the intent based on context:
   - If the symbol at line {symbol_line_no} appears to be a definition, user wants USAGES
   - If the symbol at line {symbol_line_no} appears to be a usage, user wants NAVIGATION to definition

2. Provide results in the following format:

****```yaml
intent: # either "navigation" or "usage"
results:
  - line_no: # 1-based line number 
    excerpt: "# Brief excerpt of the line content - ALWAYS quote this string"
  # For navigation: only ONE result (the definition)
  # For usage: ALL usage locations (not the definition)
****```

- Do not explain your reasoning
- Do not output any extra formatting or prose
- If no results found, return empty array: results: []

Provide exactly one YAML document.
""".strip()
    else:
        # Multiple files scenario
        return f"""
# Context from other repository files (with line numbers)

{file_context}

# Context from the current file (with line numbers)

## {current_path}

****```python
{add_line_numbers(code)}
****```

# Symbol Analysis Request

name: {symbol}
current_line: {symbol_line_no}
current_file: {current_path}

# Instructions

1. First, determine the intent based on context:
   - If the symbol at line {symbol_line_no} in {current_path} appears to be a definition, user wants USAGES
   - If the symbol at line {symbol_line_no} in {current_path} appears to be a usage, user wants NAVIGATION to definition

2. Provide results in the following format:

****```yaml
intent: # either "navigation" or "usage"
results:
  - file_path: # The exact file header shown above (case-sensitive)
    line_no: # 1-based line number
    excerpt: "# Brief excerpt of the line content - ALWAYS quote this string"
  # For navigation: only ONE result (the definition)
  # For usage: ALL usage locations across all files (not the definition)
****```

- Search ALL provided files
- Do not explain your reasoning
- Do not output any extra formatting or prose
- Do not guess or fabricate file paths or line content
- If no results found, return empty array: results: []
- File paths MUST match exactly the headers shown above

Provide exactly one YAML document.
""".strip()


def call_llm(api: ExtensionAPI, model: str, messages: List[Dict[str, str]]):
    client = OpenAI(api_key=api.api_key, base_url=OPEN_ROUTER_URL)

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=512,
        temperature=0.3,
        top_p=0.8,
        n=1,
    )

    result = response.choices[0].message.content

    api.log(f"LLM response:\n {result}")

    result = extract_code_block(result)

    assert result is not None, 'no YAML output found in the response'

    output = yaml.safe_load(result.strip('\n'))

    assert 'intent' in output, 'intent not found in the response'
    assert 'results' in output, 'results not found in the response'

    intent = output['intent']
    results = output['results']

    api.log(f"Determined intent: {intent}")

    if not results:
        api.log(f"No results found for intent: {intent}")
        return

    # for navigation, we expect only one result
    if intent == 'navigation' and len(results) > 1:
        api.log("Multiple definitions found, using the first one")
        results = results[:1]

    formatted_results = []
    for result in results:
        if isinstance(result, dict):
            file_path = result.get('file_path', api.current_file.path)
            line_no = result['line_no']
            excerpt = result.get('excerpt', '')

            formatted_results.append({
                'file_path': file_path,
                'line_number': line_no,
                'excerpt': excerpt
            })

    api.send_symbol_results(intent, formatted_results)


def extension(api: ExtensionAPI):
    current_file_path = api.current_file.path
    current_file_content = api.current_file.get_content()
    symbol = api.symbol
    symbol_line_number = api.cursor_row

    if len(api.opened_files) == 0:
        prompt = get_prompt(current_file_content, symbol, symbol_line_number)
    else:
        file_context = ''
        for opened_file in api.opened_files:
            file_context += f'## {opened_file.path}' + '\n\n'
            file_context += add_line_numbers(opened_file.get_content()) + '\n\n'
        prompt = get_prompt(current_file_content, symbol, symbol_line_number, file_context, current_file_path)

    system_prompt = get_system_prompt()
    model = 'mistralai/devstral-small'

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': prompt}
    ]
    
    api.log(f'symnol {symbol}, line_number {symbol_line_number}')

    api.log(f"Symbol analysis prompt:\n {prompt}")

    call_llm(api, model, messages)
