from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user
from models import db, Registered_Users, User

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # Шаг 1: только логин
        if 'user_login' in request.form and 'password' not in request.form:
            user_login = request.form.get('user_login', '').strip()
            user = User.query.filter_by(user_login=user_login).first()

            if user is None:
                flash(f'Логин «{user_login}» не найден. Обратитесь к администратору.', 'danger')
                return render_template('login.html')

            if not user.is_registered:
                return redirect(url_for('auth.register', user_login=user.user_login))

            return render_template('login.html',
                                   ask_password=True,
                                   user_login=user.user_login,
                                   full_name=user.full_name)

        # Шаг 2: пароль
        if 'password' in request.form:
            user_login = request.form.get('user_login', '').strip()
            password = request.form.get('password', '')

            user = User.query.filter_by(user_login=user_login).first()
            if user is None:
                flash('Пользователь не найден', 'danger')
                return redirect(url_for('auth.login'))

            account = Registered_Users.query.filter_by(username=user_login).first()
            if account is None:
                user.is_registered = False
                db.session.commit()
                return redirect(url_for('auth.register', user_login=user.user_login))

            if not account.check_password(password):
                flash('Неверный пароль', 'danger')
                return render_template('login.html',
                                       ask_password=True,
                                       user_login=user.user_login,
                                       full_name=user.full_name)

            login_user(account)
            return redirect(url_for('main.index'))

    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        user_login = request.args.get('user_login', '').strip()
        if not user_login:
            return redirect(url_for('auth.login'))

        user = User.query.filter_by(user_login=user_login).first()
        if user is None:
            flash('Пользователь не найден', 'danger')
            return redirect(url_for('auth.login'))
        if user.is_registered:
            flash('Этот пользователь уже зарегистрирован. Войдите.', 'warning')
            return redirect(url_for('auth.login'))

        return render_template('register.html',
                               user_login=user.user_login,
                               full_name=user.full_name)

    # POST
    user_login = request.form.get('user_login', '').strip()
    password = request.form.get('password', '')
    password2 = request.form.get('password2', '')

    user = User.query.filter_by(user_login=user_login).first()
    if user is None:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('auth.login'))
    if user.is_registered:
        flash('Этот пользователь уже зарегистрирован', 'warning')
        return redirect(url_for('auth.login'))
    if not password or not password2:
        flash('Заполните все поля', 'danger')
        return render_template('register.html',
                               user_login=user_login,
                               full_name=user.full_name)
    if password != password2:
        flash('Пароли не совпадают', 'danger')
        return render_template('register.html',
                               user_login=user_login,
                               full_name=user.full_name)

    account = Registered_Users(username=user_login)
    account.set_password(password)
    db.session.add(account)

    user.is_registered = True
    db.session.commit()

    login_user(account)
    return redirect(url_for('main.index'))


@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))   # обратите внимание: 'auth.login'