#!/usr/bin/env python3
"""Build a distribution-specific OpenClaw image from explicitly locked inputs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_support.images import main
if __name__ == "__main__":
    main()
