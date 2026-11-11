# This is a helper to run migrations if needed in a CI environment
import os
os.system('python manage.py migrate')