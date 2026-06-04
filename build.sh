#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Compile static assets and run database migrations
python manage.py collectstatic --no-input
python manage.py migrate