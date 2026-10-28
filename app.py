from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import select, func, join, outerjoin
from collections import defaultdict
from datetime import date, datetime
from models import db, Registered_Users, User

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me-to-random-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///objects.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

from blueprints.auth import auth
from blueprints.main import main
from blueprints.objects_bp import objects_bp

app.register_blueprint(auth)
app.register_blueprint(main)
app.register_blueprint(objects_bp, url_prefix='/objects')

@login_manager.user_loader
def load_user(user_id):
    return Registered_Users.query.get(int(user_id))


# ---------- ГЛАВНАЯ ----------
# @app.route('/')
# @login_required
# def index():
    # return render_template('index.html')

# ================== СОЗДАНИЕ БД ==================
# ВАЖНО: этот блок выполняется при импорте модуля.
# Благодаря тому, что все модели импортированы СРАЗУ после from models import ...,
# они уже зарегистрированы в db.metadata к моменту вызова create_all().
with app.app_context():
    db.create_all()
    # В КОНЕЧНОМ ВАРИАНТЕ ЭТОЙ ЧАСТИ НЕ БУДЕТ. ОНА ЗДЕСЬ ВРЕМЕННО ДЛЯ ПРОВЕРКИ, КАК ВЫГЛЯДЯТ ТАБЛИЦЫ
    if User.query.count() == 0:
        db.session.add_all([
            User(full_name='admin', position='', access_level=1, email='',
                 phone='', user_login='admin',  is_registered=False),
        ])
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True)