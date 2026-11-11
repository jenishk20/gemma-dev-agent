#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    try:
        from django.core.management import executeFromCommandLine
    except ImportError:
        raise RuntimeError("Django not installed")
    executeFromCommandLine(sys.argv)

if __name__ == '__main__':
    main()