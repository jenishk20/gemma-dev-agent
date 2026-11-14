#!/usr/bin/env python
import os
import sys
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    # Override default port to 5000 as requested
    # Note: In a real scenario, we'd pass this to the command line
    # but we can set it via sys.argv if we want to automate the runserver call.
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        sys.argv.append('0.0.0.0:5000')
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    execute_from_command_line(sys.argv)