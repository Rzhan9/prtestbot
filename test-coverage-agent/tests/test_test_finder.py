import os
import sys

# Configure sys.path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from test_coverage_agent.test_finder import find_related_tests

def test_find_related_tests_perfect_match(tmp_path):
    # Setup mock repository layout
    repo_root = tmp_path
    
    # Create source file
    src_dir = repo_root / "src" / "math"
    src_dir.mkdir(parents=True)
    src_file = src_dir / "calculator.py"
    src_file.write_text("def add(a, b): return a + b")
    
    # Create test files
    tests_dir = repo_root / "tests"
    tests_dir.mkdir()
    
    test_calc = tests_dir / "test_calculator.py"
    test_calc.write_text("def test_add(): pass")
    
    test_other = tests_dir / "test_other.py"
    test_other.write_text("def test_other(): pass")
    
    # Run finder
    # Source file path relative to repo_root
    source_rel = os.path.relpath(src_file, repo_root)
    matches = find_related_tests(source_rel, str(repo_root))
    
    assert len(matches) >= 1
    assert "tests/test_calculator.py" in matches[0] or "test_calculator.py" in matches[0]

def test_find_related_tests_mirrored_folders(tmp_path):
    repo_root = tmp_path
    
    # Create source file: src/utils/string_helper.py
    src_dir = repo_root / "src" / "utils"
    src_dir.mkdir(parents=True)
    src_file = src_dir / "string_helper.py"
    src_file.write_text("")
    
    # Create test files:
    # 1. tests/utils/test_string_helper.py (Should be highest score)
    # 2. tests/test_string_helper.py (Secondary score)
    # 3. tests/utils/test_other.py (No name match but folder match, shouldn't match base name score unless base matches, score should be lower or 0)
    
    tests_utils_dir = repo_root / "tests" / "utils"
    tests_utils_dir.mkdir(parents=True)
    
    t1 = tests_utils_dir / "test_string_helper.py"
    t1.write_text("")
    
    tests_root_dir = repo_root / "tests"
    t2 = tests_root_dir / "test_string_helper.py"
    t2.write_text("")
    
    source_rel = os.path.relpath(src_file, repo_root)
    matches = find_related_tests(source_rel, str(repo_root))
    
    # First match should be the mirrored one: tests/utils/test_string_helper.py
    assert len(matches) >= 2
    assert matches[0].replace(os.sep, '/') == "tests/utils/test_string_helper.py"
    assert matches[1].replace(os.sep, '/') == "tests/test_string_helper.py"
