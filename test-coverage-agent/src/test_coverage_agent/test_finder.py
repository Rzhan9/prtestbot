import os
from typing import List

def find_related_tests(source_file: str, repo_root: str) -> List[str]:
    """
    Given a source file path (relative to repo_root), searches the repository
    for test files that are relevant to it.
    """
    if not source_file.endswith('.py'):
        return []
        
    base_name = os.path.splitext(os.path.basename(source_file))[0]
    
    # List of directories to exclude from the walk to optimize speed and avoid noise
    exclude_dirs = {
        '.git', '.github', '__pycache__', '.pytest_cache', '.venv', 'venv', 
        'env', 'build', 'dist', 'node_modules', '.agents', '.gemini'
    }
    
    test_files = []
    for root, dirs, files in os.walk(repo_root):
        # Prune excluded directories in-place
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if not file.endswith('.py'):
                continue
            
            # Get path relative to the repo_root
            rel_dir = os.path.relpath(root, repo_root)
            full_rel_path = file if rel_dir == '.' else os.path.join(rel_dir, file)
            
            # Standard Python test file naming check
            is_test = (
                file.startswith('test_') or 
                file.endswith('_test.py') or 
                'tests/' in full_rel_path or 
                'test/' in full_rel_path
            )
            if is_test:
                test_files.append(full_rel_path)
                
    # Score candidates based on matching patterns
    scored_tests = []
    for test_file in test_files:
        score = 0
        test_base = os.path.splitext(os.path.basename(test_file))[0]
        
        # Perfect matching base name: test_calc vs calc or calc_test vs calc
        if test_base == f"test_{base_name}" or test_base == f"{base_name}_test":
            score += 100
        # If the test file name contains the source file name as a substring (e.g. test_calc_extra)
        elif base_name in test_base:
            score += 50
            
        # Check folder similarity (excluding standard packaging/test folders like src, app, tests)
        src_parts = source_file.split(os.sep)
        test_parts = test_file.split(os.sep)
        
        src_dirs = [p for p in src_parts[:-1] if p not in ('src', 'app')]
        test_dirs = [p for p in test_parts[:-1] if p not in ('tests', 'test', 'unit', 'integration')]
        
        matching_dirs = set(src_dirs) & set(test_dirs)
        score += len(matching_dirs) * 20
        
        if score > 0:
            scored_tests.append((score, test_file))
            
    # Sort descending by score
    scored_tests.sort(key=lambda x: x[0], reverse=True)
    
    # Return top 3 matches
    return [test_file for score, test_file in scored_tests[:3]]
