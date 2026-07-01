import requests
from typing import List, Dict, Any

class GitHubClient:
    """
    Client for interacting with the GitHub REST API.
    """
    def __init__(self, token: str, repo: str):
        self.token = token
        self.repo = repo  # Expected format: "owner/repo"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.base_url = f"https://api.github.com/repos/{repo}"

    def get_pr_details(self, pr_number: int) -> Dict[str, Any]:
        """
        Fetches metadata for the pull request (title, body, draft, etc.)
        """
        url = f"{self.base_url}/pulls/{pr_number}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_pr_diff(self, pr_number: int) -> str:
        """
        Fetches the unified diff of the PR.
        """
        url = f"{self.base_url}/pulls/{pr_number}"
        headers = dict(self.headers)
        # Using media type application/vnd.github.diff returns raw diff format
        headers["Accept"] = "application/vnd.github.diff"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text

    def get_pr_comments(self, pr_number: int) -> List[Dict[str, Any]]:
        """
        Lists comments on the PR issue.
        """
        url = f"{self.base_url}/issues/{pr_number}/comments"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def create_comment(self, pr_number: int, body: str) -> Dict[str, Any]:
        """
        Creates a new comment on the PR.
        """
        url = f"{self.base_url}/issues/{pr_number}/comments"
        response = requests.post(url, headers=self.headers, json={"body": body})
        response.raise_for_status()
        return response.json()

    def update_comment(self, comment_id: int, body: str) -> Dict[str, Any]:
        """
        Updates an existing comment.
        """
        url = f"{self.base_url}/issues/comments/{comment_id}"
        response = requests.patch(url, headers=self.headers, json={"body": body})
        response.raise_for_status()
        return response.json()
