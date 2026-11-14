#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    try:
        import from django.core.management import execute_from_command_line
    except ImportError:
        try:
            from django.core.management import execute_from_command_line
        except ImportError:
            raise ImportError("Django not installed")
    
    # Overriding the default port to 5000 as requested
    sys.argv.append('0.0.0.0:5000') if len(sys.argv) == 1 else None
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()