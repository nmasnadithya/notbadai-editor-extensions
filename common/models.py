# Default model mappings
MODELS = {
    'v3': {'openrouter': 'deepseek/deepseek-chat-v3-0324'},
    'r1': {'openrouter': 'deepseek/deepseek-r1-0528'},  # Deepseek model with 64k context
    'o3': {'openrouter': 'openai/o3'},  # OpenAI model
    'magistral': {'openrouter': 'mistralai/magistral-small-2506'},
    'devstral': {'openrouter': 'mistralai/devstral-medium'},
    'default': {
        'deepinfra': 'Qwen/Qwen3-Coder-480B-A35B-Instruct-Turbo',
        'openrouter': 'qwen/qwen3-coder'
    },
    'c4': {'openrouter': 'anthropic/claude-sonnet-4'},
    'grok': {'openrouter': 'x-ai/grok-4'},
    'k2': {'openrouter': 'moonshotai/kimi-k2'},
    'qwen': {
        'deepinfra': 'Qwen/Qwen3-Coder-480B-A35B-Instruct-Turbo',
        'openrouter': 'qwen/qwen3-coder'
    },
}