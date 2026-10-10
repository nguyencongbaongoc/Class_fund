import sys
from pathlib import Path

# Add backend directory to sys.path and import implementation
backend_dir = Path(__file__).resolve().parent.parent / "class-fund-backend-v0.1" / "class-fund-backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.failover_manager import (
    FailoverManager,
    FailoverConfig,
    MySQLNodeConfig,
    main,
)

if __name__ == "__main__":
    main()
