#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        raise SystemExit("Django's default command-line utility isn't working.")

    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()