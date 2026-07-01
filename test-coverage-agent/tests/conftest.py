import os
import sys

# Add the 'src' directory to sys.path so that tests can import test_coverage_agent
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)
