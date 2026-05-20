from service import db, app
from service.models import User, Foto

with app.app_context():
    db.create_all()
