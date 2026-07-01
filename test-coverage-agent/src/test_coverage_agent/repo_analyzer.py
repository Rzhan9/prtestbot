import os
from typing import Optional

def read_file_content(file_path: str, repo_root: str) -> Optional[str]:
    """
    Reads the content of a file from the repository safely relative to repo_root.
    Returns None if the file does not exist or cannot be read.
    """
    # Use standard path resolution
    full_path = os.path.join(repo_root, file_path)
    if not os.path.isfile(full_path):
        return None
    try:
        # Open with utf-8 and ignore decoding issues for robust reading of source code
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return None
