#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    try:
        import numpy as np
    except ImportError:
        pass
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        raise RuntimeError("Django not installed")
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()