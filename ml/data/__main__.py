"""
CLI entrypoint for ml.data
Supports:
  python -m ml.data readiness
"""

import sys
from ml.data.readiness import main as readiness_main

def main():
    if len(sys.argv) > 1 and sys.argv[1].lower() == "readiness":
        readiness_main()
    else:
        # Default action
        readiness_main()

if __name__ == "__main__":
    main()
