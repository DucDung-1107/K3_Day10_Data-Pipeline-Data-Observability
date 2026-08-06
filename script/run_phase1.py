from __future__ import annotations

import os
import sys
# Ensure the src directory is in the Python path for module resolution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.pipelines.phase1 import main


if __name__ == "__main__":
    main()
