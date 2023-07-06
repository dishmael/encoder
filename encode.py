#!/usr/bin/env python3

import os
import sys

from media import Encoder

# Entry point
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: main.py <file>")
        sys.exit(-1)

    e = Encoder(sys.argv[1])
    e.encode()
