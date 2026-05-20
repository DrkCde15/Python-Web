from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

base_dir = Path(__file__).resolve().parent.parent

app = Flask(__name__, template_folder=base_dir / 'templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(base_dir / 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from service import routes
