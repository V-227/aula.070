import os
import requests
from flask import Flask, render_template, session, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurações do Mailgun
TO_EMAILS = ['flaskaulasweb@zohomail.com','sena.vinicius@aluno.ifsp.edu.br']

bootstrap = Bootstrap(app)
moment = Moment(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

def send_email(subject, body):
    return requests.post(
        "https://api.mailgun.net/v3/sandbox20203c57442e40e8a64987c0f0bbf1c4.mailgun.org/messages",
        auth=("api", "1065c4fdda73bd999f7b7be3e5ad70fa-911539ec-ebd11a15"),  # Corrigido para passar uma tupla
        data={"from": "Excited User <mailgun@sandbox20203c57442e40e8a64987c0f0bbf1c4.mailgun.org>",
              "to": TO_EMAILS,
              "subject": subject,
              "text": body}
    )


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
        return '<User %r>' % self.username

class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    role = SelectField('What is your role?', choices=[
        ('user', 'User'),
        ('admin', 'Administrator'),
        ('moderator', 'Moderator')  # Adicionando a opção de Moderator
    ])
    submit = SubmitField('Submit')

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            role = Role.query.filter_by(name=form.role.data).first()
            if role is None:
                role = Role(name=form.role.data)
                db.session.add(role)
                db.session.commit()
            user = User(username=form.name.data, role=role)
            db.session.add(user)
            db.session.commit()
            session['known'] = False

            # Enviar e-mail após o cadastro de um novo usuário
            response = send_email(
                subject="Novo usuário cadastrado",
                body=f"Usuário {user.username} foi cadastrado com sucesso com a função {role.name}."
            )

            # Adicionar um feedback sobre o envio do e-mail
            if response.status_code == 200:
                print("E-mail enviado com sucesso.")
            else:
                print(f"Falha no envio do e-mail: {response.status_code} - {response.text}")

        else:
            session['known'] = True
        session['name'] = form.name.data
        session['role'] = form.role.data
        return redirect(url_for('index'))

    # Consultar todos os usuários e funções
    users = User.query.all()
    roles = Role.query.all()

    # Contagem de usuários
    total_users = len(users)

    # Agrupamento de usuários por função
    users_by_role = {}
    for role in roles:
        users_by_role[role.name] = User.query.filter_by(role=role).all()

    return render_template('index.html', form=form, name=session.get('name'),
                           known=session.get('known', False), users=users,
                           total_users=total_users, users_by_role=users_by_role)

if __name__ == '__main__':
    app.run(port=5001, debug=True)
