import os
import sys
from pathlib import Path

# Set up test environment
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["AI_CONFIDENCE_THRESHOLD"] = "0.9"

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "class-fund-backend-v0.1" / "class-fund-backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

backend_tests_dir = backend_dir / "tests"
if str(backend_tests_dir) not in sys.path:
    sys.path.insert(0, str(backend_tests_dir))

# Import all fixtures from backend conftest
from tests.conftest import *  # noqa: F401, F403
