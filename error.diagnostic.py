import yaml
from typing import List, Dict

from openai import OpenAI

from common.api import ExtensionAPI
from common.utils import add_line_numbers, extract_code_block
from common.secrets import OPEN_ROUTER_TOKEN, OPEN_ROUTER_URL

def get_prompt(code: str) -> str:
    return f"""
You are an expert Python code reviewer. Your goal is to find every syntax error in the code snippet below, referring exactly to its line number.

# Python code (with line numbers)

```python
{add_line_numbers(code)}
```

# Instructions

Carefully analyze the code above and identify **all** the syntax errors. 
For each error, output one YAML entry with these two fields:

```yaml
  line_no:         # the exact line number where the syntax error occurs
  description:     # explanation of the syntax error (do not supply corrected code)
```

- Always use the provided line numbers.
- Identify only syntax errors.
- Do not identify bugs or logic errors in code, only identify syntax errors.
- Identify all syntax errors, each as a separate YAML entry.
- Do not include any prose, lists, or formatting outside the YAML block.
- Return an empty YAML document if there are no syntax errors

Provide exactly one YAML document listing all syntax-error entries.
""".strip()

def call_llm(api: ExtensionAPI, model: str, messages: List[Dict[str, str]]):
    client = OpenAI(api_key=OPEN_ROUTER_TOKEN, base_url=OPEN_ROUTER_URL)
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=1024,
        temperature=0.8,
        top_p=0.8,
        n=1,
    )
    
    result = response.choices[0].message.content
    
    api.log(f"LLM response:\n {result}")
    
    result = extract_code_block(result)
    
    assert result is not None, 'no YAML output found in the response'
    
    errors = yaml.safe_load(result.strip('\n'))
    
    res = []
    for error in errors:
        res.append(dict(line_number=error["line_no"], description=error["description"]))
        
    api.send_diagnostics(res)


def extension(api: ExtensionAPI):
    current_file_content = api.current_file.get_content()
    
    model = 'deepseek/deepseek-chat-v3-0324'
    
    prompt = get_prompt(current_file_content)
    
    messages = [
        {'role': 'user', 'content': prompt}
    ]
    
    api.log(f"prompt:\n {prompt}")
    
    call_llm(api, model, messages)
    