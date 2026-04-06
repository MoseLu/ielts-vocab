#!/usr/bin/env python
"""Speech service entrypoint."""

import os
import sys
from pathlib import Path


backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from speech_service import print_banner, run_server


if __name__ == '__main__':
    print_banner()
    run_server()
