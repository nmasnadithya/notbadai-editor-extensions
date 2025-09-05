from git import Repo


class GitClient:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.repo = Repo(project_path)

    def is_repository(self) -> bool:
        """Check if the current directory is a git repository."""
        return not self.repo.bare

    def get_commit_diff(self, staged_only: bool = False) -> str:
        if staged_only:
            # Get diff of staged files only
            return self.repo.git.diff('--cached')
        else:
            # Get diff of all modified files (staged and unstaged)
            return self.repo.git.diff('HEAD')

    def commit_push(self, commit_message: str) -> None:
        """Commit all changes and push to the current branch."""
        # Stage all changes
        self.repo.git.add('-A')

        # Check if there are changes to commit
        if self.repo.is_dirty() or self.repo.untracked_files:
            # Commit changes
            commit = self.repo.index.commit(commit_message)

            # Get changed files - commit.stats.files.keys() already returns file paths as strings
            changed_files = list(commit.stats.files.keys())

            # Push to current branch
            origin = self.repo.remote('origin')
            current_branch = self.repo.active_branch.name

            # Try to push with upstream
            origin.push(f"{current_branch}:{current_branch}", set_upstream=True)