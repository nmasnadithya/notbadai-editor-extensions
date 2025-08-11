from typing import List, Dict, Any
import json

system_prompt = """
You are an expert programmer assisting a colleague in adding code to an existing file.

Your colleague will give you:
• The surrounding code (context)  
• Clear instructions describing the snippet to add

Your task:
• Provide exactly 4 different suggestions for the next line of code
• Match the file's indentation, style, and conventions
• Do *not* include explanations or comments

You MUST respond with valid JSON in this EXACT format:
{
  "suggestions": [
    "first code line suggestion",
    "second code line suggestion", 
    "third code line suggestion",
    "fourth code line suggestion"
  ]
}

Each suggestion should be a complete, valid line of code. No markdown, no backticks, no extra formatting.
""".strip()


def get_single_file_prompt(prefix: str, suffix: str) -> List[Dict[str, str]]:
    lines = prefix.split("\n")
    prefix_lines = '\n'.join(lines[:-1])
    last_line = lines[-1]

    user_content = "First, I will give you some potentially helpful context about my code.\nThen, I will show you the insertion point and give you the instruction.\n\n# Context\n\n```python\n"
    user_content += prefix_lines + "\n# INSERT_YOUR_NEXT_LINE"
    
    if suffix.strip() != '':
        lines = suffix.split("\n")
        suffix_lines = '\n'.join(lines[:-1])
        user_content += suffix_lines
    
    user_content += "\n```\n\n## Instructions\n\n"
    user_content += "Provide exactly 4 different suggestions for what the next line of code should be. Return your response as JSON with a 'suggestions' array containing 4 strings.\n"
    
    if last_line.strip():
        user_content += f'\nThe next line begins with `{last_line}`.'

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]


def get_multi_file_prompt(prefix: str, suffix: str, file_context: str, current_file_name: str) -> List[Dict[str, str]]:
    lines = prefix.split("\n")
    prefix_lines = '\n'.join(lines[:-1])
    last_line = lines[-1]

    user_content = "I'll start by giving you some potentially helpful context about my code.\n"
    user_content += "First, I'll provide context on the other repository files relevant to this task, followed by context on the code I'm currently editing. "
    user_content += "Then, I will show you the insertion point and give you the instruction.\n\n"
    
    user_content += "## Context from Other Repository Files\n\n"
    user_content += file_context

    user_content += f"\n\n## Context for the Current File\n\n# {current_file_name}\n\n```python\n"
    user_content += prefix_lines + "\n# INSERT_YOUR_NEXT_LINE"
    
    if suffix.strip() != '':
        lines = suffix.split("\n")
        suffix_lines = '\n'.join(lines[:-1])
        user_content += suffix_lines
    
    user_content += "\n```\n\n## Instructions\n\n"
    user_content += "Provide exactly 4 different suggestions for what the next line of code should be. Return your response as JSON with a 'suggestions' array containing 4 strings.\n"
    user_content += "Avoid repeating any lines in the vicinity of the current one (e.g., those directly before or after).\n"
    
    if last_line.strip():
        user_content += f'\nThe next line begins with `{last_line}`.'

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]


def parse_response(response: str) -> List[str]:
    try:
        # Clean up response - remove any markdown code blocks if present
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        elif response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        
        # Parse JSON
        data = json.loads(response.strip())
        
        # Extract suggestions - ensure we have exactly what we expect
        if isinstance(data, dict) and 'suggestions' in data:
            suggestions = data['suggestions']
            if isinstance(suggestions, list):
                # Return up to 4 suggestions, filter out empty ones
                valid_suggestions = [str(suggestion).strip() for suggestion in suggestions if str(suggestion).strip()]
                return valid_suggestions[:4]  # Limit to 4 suggestions max
        
        return []
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Failed to parse response as JSON: {e}")
        print(f"Raw response: {response}")
        return []  # Return empty list on parse failure for consistency







