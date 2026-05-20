from datetime import datetime

from service import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(120), nullable=False)
    fotos = db.relationship('Foto', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'
    
class Foto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imagem = db.Column(db.String(200), default='default.png', nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Foto {self.imagem}>'
