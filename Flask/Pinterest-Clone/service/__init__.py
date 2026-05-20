from pathlib import Path
from flask import Flask

base_dir = Path(__file__).resolve().parent.parent

app = Flask(__name__, template_folder=base_dir / 'templates')

from service import routes
