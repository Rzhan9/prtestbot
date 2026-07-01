import os
import sys
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from test_coverage_agent.diff_parser import parse_diff, ChangedFile

def test_parse_diff_added_file():
    diff_text = """diff --git a/src/math.py b/src/math.py
new file mode 100644
index 0000000..f924b1a
--- /dev/null
+++ b/src/math.py
@@ -0,0 +1,3 @@
+def add(a, b):
+    return a + b
+
"""
    files = parse_diff(diff_text)
    assert len(files) == 1
    assert files[0].filename == "src/math.py"
    assert files[0].status == "added"
    assert files[0].is_source_file is True
    assert files[0].is_test_file is False

def test_parse_diff_modified_and_test():
    diff_text = """diff --git a/src/math.py b/src/math.py
index f924b1a..a1b2c3d 100644
--- a/src/math.py
+++ b/src/math.py
@@ -1,3 +1,6 @@
 def add(a, b):
     return a + b
+
+def subtract(a, b):
+    return a - b
diff --git a/tests/test_math.py b/tests/test_math.py
new file mode 100644
index 0000000..e69de29
--- /dev/null
+++ b/tests/test_math.py
@@ -0,0 +1,4 @@
+from src.math import add
+def test_add():
+    assert add(1, 2) == 3
"""
    files = parse_diff(diff_text)
    assert len(files) == 2
    
    assert files[0].filename == "src/math.py"
    assert files[0].status == "modified"
    assert files[0].is_source_file is True
    assert files[0].is_test_file is False
    
    assert files[1].filename == "tests/test_math.py"
    assert files[1].status == "added"
    assert files[1].is_source_file is False
    assert files[1].is_test_file is True

def test_parse_diff_deleted_file():
    diff_text = """diff --git a/src/old_file.py b/src/old_file.py
deleted file mode 100644
index f924b1a..0000000
--- a/src/old_file.py
+++ /dev/null
@@ -1,30000 -0,0 @@
-def old():
-    pass
"""
    files = parse_diff(diff_text)
    assert len(files) == 1
    assert files[0].filename == "src/old_file.py"
    assert files[0].status == "deleted"
