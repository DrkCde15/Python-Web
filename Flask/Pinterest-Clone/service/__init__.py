from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

base_dir = Path(__file__).resolve().parent.parent

app = Flask(__name__, template_folder=base_dir / 'templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(base_dir / 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dr67ilpo8yfdsaw3456yhjlpoiuygfds'

db = SQLAlchemy(app)
bc = Bcrypt(app)
lm = LoginManager(app)
lm.login_view = 'index'

from service import routes
