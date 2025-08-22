# wsgi.py (at repo root)
import os, sys
BASE_DIR = os.path.dirname(__file__)
# add the OUTER resilience_tracker folder to the path, so Python can see the inner package
sys.path.insert(0, os.path.join(BASE_DIR, "resilience_tracker"))

from resilience_tracker.app import create_app

app = create_app()
