MODELS = {
    'v3': 'deepseek/deepseek-chat-v3-0324',  # Regular deepseek model
    'r1': 'deepseek/deepseek-r1-0528',  # Deepseek model with 64k context
    'o3': 'openai/o3',  # OpenAI model
    'magistral': 'mistralai/magistral-small-2506',
    'devstral': 'mistralai/devstral-medium',
    'default': 'anthropic/claude-sonnet-4',
    # 'default': 'openai/o3',
    # 'default': 'anthropic/claude-opus-4',
    'c4': 'anthropic/claude-sonnet-4',
    'grok': 'x-ai/grok-4',
}


def get_model_name(model_key):
    return MODELS.get(model_key)