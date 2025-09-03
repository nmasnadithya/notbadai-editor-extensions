from common.api import ExtensionAPI
from common.diff import get_matches
from common.llm import call_llm


# https://docs.morphllm.com/api-reference/endpoint/apply

def extension(api: ExtensionAPI):
    prompt = api.prompt.rstrip()  # no left strip for indentation

    if api.current_file and api.edit_file.path == api.current_file.path:
        content = api.current_file.get_content()
    else:
        try:
            content = api.edit_file.get_content()
        except FileNotFoundError:
            content = ''

    instruction = ''

    messages = [
        {
            "role": "user",
            "content": f"<instructions>{instruction}</instructions>\n<code>f{content}</code>\n<update>{prompt}</update>"
        }
    ]

    merged_code = call_llm(api,
                           'morph_large',
                           messages,
                           push_to_chat=False,
                           )
    matches, cleaned_patch = get_matches(content, merged_code)
    api.apply_diff(cleaned_patch, matches)
