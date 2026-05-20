from flask import render_template
from service import app

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/perfil/<user>')
def perfil(user):
    return render_template('perfil.html', user=user)
