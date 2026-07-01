import re
from typing import List

class ChangedFile:
    """
    Represents a file changed in the pull request.
    """
    def __init__(self, filename: str, status: str, diff_hunk: str):
        self.filename = filename
        self.status = status  # 'added', 'modified', or 'deleted'
        self.diff_hunk = diff_hunk

    @property
    def is_source_file(self) -> bool:
        """
        Determines if the file is a Python source file (excluding tests).
        Can be extended to support other languages.
        """
        if not self.filename.endswith('.py'):
            return False
        return not self.is_test_file

    @property
    def is_test_file(self) -> bool:
        """
        Determines if the file is a Python test file by naming convention or directory.
        """
        if not self.filename.endswith('.py'):
            return False
        parts = self.filename.split('/')
        basename = parts[-1]
        return (
            basename.startswith('test_') or 
            basename.endswith('_test.py') or 
            'tests/' in self.filename or 
            'test/' in self.filename
        )

    def __repr__(self) -> str:
        return f"ChangedFile(filename='{self.filename}', status='{self.status}', is_test={self.is_test_file})"


def parse_diff(diff_text: str) -> List[ChangedFile]:
    """
    Parses a unified diff string and returns a list of ChangedFile objects.
    """
    if not diff_text:
        return []
    
    files = []
    lines = diff_text.splitlines()
    
    current_file = None
    current_status = "modified"
    current_diff_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("diff --git "):
            # Save the previous file if one was in progress
            if current_file and current_diff_lines:
                files.append(ChangedFile(current_file, current_status, "\n".join(current_diff_lines)))
            
            # Reset state for the new file diff block
            current_file = None
            current_status = "modified"
            current_diff_lines = [line]
            
            # Parse paths and status from headers
            filename = None
            i += 1
            while i < len(lines) and not lines[i].startswith("diff --git "):
                sub_line = lines[i]
                current_diff_lines.append(sub_line)
                
                if sub_line.startswith("new file mode "):
                    current_status = "added"
                elif sub_line.startswith("deleted file mode "):
                    current_status = "deleted"
                elif sub_line.startswith("--- "):
                    pass
                elif sub_line.startswith("+++ "):
                    path_part = sub_line[4:]
                    if path_part != "/dev/null":
                        # Remove b/ prefix
                        if path_part.startswith("b/"):
                            filename = path_part[2:]
                        else:
                            filename = path_part
                i += 1
            
            # Fallback if we didn't find the filename from +++ (e.g. deleted files or special headers)
            if not filename:
                match = re.match(r"diff --git a/(.*) b/(.*)", line)
                if match:
                    filename = match.group(2) if current_status != "deleted" else match.group(1)
            
            current_file = filename
            # Adjust index since the inner loop consumed the next 'diff --git' boundary check
            i -= 1
        else:
            if current_file:
                current_diff_lines.append(line)
        i += 1
        
    if current_file and current_diff_lines:
        files.append(ChangedFile(current_file, current_status, "\n".join(current_diff_lines)))
        
    return files
