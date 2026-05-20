from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/perfil/<user>')
def perfil(user):
    return render_template('perfil.html', user=user)

if __name__ == '__main__':
    app.run(debug=True)