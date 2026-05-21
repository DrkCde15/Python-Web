from flask import render_template, redirect, url_for
from service import app, db, bc
from flask_login import login_required, login_user, logout_user, current_user
from service.forms import LoginForm, CriarContaForm, FormFoto
from service.models import User, Foto
import os
from werkzeug.utils import secure_filename

@app.route('/', methods=['GET', 'POST'])
def index():
    formlogin = LoginForm()
    if formlogin.validate_on_submit():
        user = User.query.filter_by(email=formlogin.email.data).first()
        if user and bc.check_password_hash(user.senha, formlogin.password.data):
            login_user(user, remember=True)
            return redirect(url_for('perfil', id=user.id))
    return render_template('index.html', form=formlogin)

@app.route('/criar-conta', methods=['GET', 'POST'])
def criar_conta():
    formcriarconta = CriarContaForm()
    if formcriarconta.validate_on_submit():
        pswd = bc.generate_password_hash(formcriarconta.password.data)
        user = User(username=formcriarconta.username.data, 
                    email=formcriarconta.email.data, 
                    senha=pswd)
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)
        return redirect(url_for('index'))
    return render_template('criar_conta.html', form=formcriarconta)

@app.route('/perfil/<id>', methods=['GET', 'POST'])
@login_required
def perfil(id):
    if int(id) == int(current_user.id):
        formfoto = FormFoto()
        if formfoto.validate_on_submit():
            foto_file = formfoto.foto.data
            filename = secure_filename(foto_file.filename)
            foto_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            foto_file.save(foto_path)
            nova_foto = Foto(imagem=filename, user_id=current_user.id)
            db.session.add(nova_foto)
            db.session.commit()
        return render_template('perfil.html', user=current_user, formfoto=formfoto)
    else:
        user = User.query.get(int(id))
        return render_template('perfil.html', user=user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/excluir-conta')
@login_required
def excluir_conta():
    user = current_user
    db.session.delete(user)
    db.session.commit()
    logout_user()
    return redirect(url_for('index'))
