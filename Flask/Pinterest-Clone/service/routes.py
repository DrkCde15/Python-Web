from flask import render_template
from service import app
from flask_login import login_required
from service.forms import LoginForm, CriarContaForm

@app.route('/', methods=['GET', 'POST'])
def index():
    formlogin = LoginForm()
    if formlogin.validate_on_submit():
        pass
    return render_template('index.html', form=formlogin)

@app.route('/criar-conta', methods=['GET', 'POST'])
def criar_conta():
    formcriarconta = CriarContaForm()
    if formcriarconta.validate_on_submit():
        pass
    return render_template('criar_conta.html', form=formcriarconta)

@app.route('/perfil/<user>')
@login_required
def perfil(user):
    return render_template('perfil.html', user=user)
