from common.api import ExtensionAPI, Input, Button
from common.git_client import GitClient
from common.llm import call_llm


def get_system_prompt() -> str:
    return """
You are an expert at writing clear, concise git commit messages. 

Given a git diff, write a commit message that:
1. Follows conventional commit format when appropriate (feat:, fix:, docs:, etc.)
2. Is concise but descriptive
3. Explains what was changed and why
4. Uses imperative mood (e.g., "Add", "Fix", "Update")

Return only the commit message, no additional text or formatting.
""".strip()


def generate_commit_message(api: ExtensionAPI, diff: str) -> str:
    """Generate a commit message based on the git diff."""

    if not diff.strip():
        return "Empty commit"

    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": f"Generate a commit message for this diff:\n\n```diff\n{diff}\n```"}
    ]

    api.update_progress(50, "Generating commit message...")

    commit_message = call_llm(api,
                              'qwen',
                              messages,
                              push_to_chat=False,
                              )

    commit_message = commit_message.strip().strip('"').strip("'")

    return commit_message


def extension(api: ExtensionAPI):
    """Extension that provides a commit and push interface."""

    client = GitClient(api.repo_path)
    api.log(str(api.tool_state))

    if api.tool_action == 'init':
        diff = client.get_commit_diff()
        api.log(f"Git diff:\n{diff}")

        has_changes = bool(diff.strip())

        if has_changes:
            api.update_progress(25, "Analyzing changes...")
            generated_message = generate_commit_message(api, diff)
            api.update_progress(100, "Commit message generated")
        else:
            generated_message = "No changes to commit"

        tool_interface = [
            [
                Input(
                    name="commit_message",
                    placeholder="Enter commit message...",
                    value=generated_message
                )
            ],
            [
                Button(
                    name="Commit and Push",
                    disabled=not has_changes,
                )
            ]
        ]

        api.send_tool_interface('Source Control', tool_interface)

    elif api.tool_action == 'Commit and Push':
        commit_message = api.tool_state['commit_message'].value.strip()

        api.update_progress(50, "Committing and pushing changes...")
        client.commit_push(commit_message)
        api.update_progress(100, "Changes committed and pushed successfully")
        api.send_tool_interface('', [])
    else:
        raise ValueError('Invalid tool action')
