from flask import render_template
from service import app
from flask_login import login_required, current_user


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/perfil/<user>')
@login_required
def perfil(user):
    return render_template('perfil.html', user=user)
