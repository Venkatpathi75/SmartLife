#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Run database table initialization
python -c "from app import create_app, db; app = create_app('production'); app.app_context().push(); db.create_all()"
