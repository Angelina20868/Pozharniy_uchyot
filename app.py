from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import select, func, join, outerjoin
from collections import defaultdict


# 1) Импортируем db И ВСЕ МОДЕЛИ — это гарантирует, что они зарегистрируются
#    в db.metadata ДО вызова db.init_app и db.create_all
from models import (
    db,
    Registered_Users,
    User,
    Divisions,
    UsersAtDivisions,
    Attestations,
    UsersAttestations,
    Vacations,
    Machines_Property,
    Technical_Maintenance,
    Forces_resources,
)

# 2) Создаём приложение (обратите внимание на __name__)
app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me-to-random-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///objects.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 3) Привязываем SQLAlchemy к приложению
db.init_app(app)

# 4) Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Registered_Users.query.get(int(user_id))


# ================== МАРШРУТЫ ==================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Шаг 1: только логин
        if 'user_login' in request.form and 'password' not in request.form:
            user_login = request.form.get('user_login', '').strip()
            user = User.query.filter_by(user_login=user_login).first()

            if user is None:
                flash(f'Логин «{user_login}» не найден. Обратитесь к администратору.', 'danger')
                return render_template('login.html')

            if not user.is_registered:
                return redirect(url_for('register', user_login=user.user_login))

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
                return redirect(url_for('login'))

            account = Registered_Users.query.filter_by(username=user_login).first()
            if account is None:
                user.is_registered = False
                db.session.commit()
                return redirect(url_for('register', user_login=user.user_login))

            if not account.check_password(password):
                flash('Неверный пароль', 'danger')
                return render_template('login.html',
                                       ask_password=True,
                                       user_login=user.user_login,
                                       full_name=user.full_name)

            login_user(account)
            return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        user_login = request.args.get('user_login', '').strip()
        if not user_login:
            return redirect(url_for('login'))

        user = User.query.filter_by(user_login=user_login).first()
        if user is None:
            flash('Пользователь не найден', 'danger')
            return redirect(url_for('login'))
        if user.is_registered:
            flash('Этот пользователь уже зарегистрирован. Войдите.', 'warning')
            return redirect(url_for('login'))

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
        return redirect(url_for('login'))
    if user.is_registered:
        flash('Этот пользователь уже зарегистрирован', 'warning')
        return redirect(url_for('login'))
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
    return redirect(url_for('index'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ---------- ГЛАВНАЯ ----------
@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/objects/<table_name>')
def objects(table_name):
    # Маппинг имён таблиц на модели
    table_map = {
        'user': User,
        'machines_property': Machines_Property,
        'technical_maintenance': Technical_Maintenance,
        'attestations': Attestations,
        'usersAttestations': UsersAttestations,
        'divisions': Divisions,
        'usersAtDivisions': UsersAtDivisions,
        'vacations': Vacations,
        'forces_resources': Forces_resources
    }

    if table_name not in table_map:
        return "Таблица не найдена", 404

    model = table_map[table_name]

    # ===== Специальная обработка: подразделения + сотрудники =====
    if table_name == 'usersAtDivisions':

        # ---------------------------------------------------------
        # ЗАПРОС 1: SELECT ... GROUP BY — подсчёт сотрудников
        # даёт в результате Эквивалент SQL:
        #   SELECT divisions.id, divisions.div_name, COUNT(user.id) AS user_count
        #   FROM divisions
        #   LEFT OUTER JOIN users_at_divisions
        #       ON users_at_divisions.div_id = divisions.id
        #   LEFT OUTER JOIN user
        #       ON user.id = users_at_divisions.user_id
        #   GROUP BY divisions.id, divisions.div_name
        # ---------------------------------------------------------
        stmt_count = (
            select(
                Divisions.id,
                Divisions.div_name,
                func.count(User.id).label('user_count')
            )
            .outerjoin(UsersAtDivisions, UsersAtDivisions.div_id == Divisions.id)
            .outerjoin(User, User.id == UsersAtDivisions.user_id)
            .group_by(Divisions.id, Divisions.div_name)
            .order_by(Divisions.id)
        )
        stats = db.session.execute(stmt_count).all()

        # ---------------------------------------------------------
        # ЗАПРОС 2: SELECT ... JOIN список сотрудников  даёт в результате Эквивалент SQL:
        #   SELECT divisions.id, divisions.div_name,
        #          user.id, user.full_name, user.user_login,
        #          user.email, user.phone
        #   FROM divisions
        #   LEFT OUTER JOIN users_at_divisions
        #       ON users_at_divisions.div_id = divisions.id
        #   LEFT OUTER JOIN user
        #       ON user.id = users_at_divisions.user_id
        #   ORDER BY divisions.id, user.full_name
        # ---------------------------------------------------------
        stmt_rows = (
            select(Divisions, User)
            .outerjoin(UsersAtDivisions, UsersAtDivisions.div_id == Divisions.id)
            .outerjoin(User, User.id == UsersAtDivisions.user_id)
            .order_by(Divisions.id, User.full_name)
        )
        rows = db.session.execute(stmt_rows).all()

        # Группируем результат по подразделениям в Python
        divisions_data = defaultdict(lambda: {
            'division': None,
            'users': [],
            'user_count': 0
        })

        for row in rows:
            div = row.Divisions
            user = row.User
            entry = divisions_data[div.id]
            entry['division'] = div
            if user is not None:
                entry['users'].append(user)

        # Подставляем счётчики из GROUP BY-запроса
        for row in stats:
            divisions_data[row.id]['user_count'] = row.user_count

        return render_template('users_at_divisions.html',
                               divisions_data=divisions_data.values())

    # ===== Остальные таблицы: обычный SELECT * FROM table =====
    # Эквивалент SQL: SELECT * FROM <table>
    stmt = select(model)
    items = db.session.execute(stmt).scalars().all()

    columns = [col.name for col in model.__table__.columns if col.name != 'id']
    return render_template('objects.html',
                           table_name=table_name,
                           items=items,
                           columns=columns)


# ================== СОЗДАНИЕ БД ==================
# ВАЖНО: этот блок выполняется при импорте модуля.
# Благодаря тому, что все модели импортированы СРАЗУ после from models import ...,
# они уже зарегистрированы в db.metadata к моменту вызова create_all().
with app.app_context():
    db.create_all()
    # В КОНЕЧНОМ ВАРИАНТЕ ЭТОЙ ЧАСТИ НЕ БУДЕТ. ОНА ЗДЕСЬ ВРЕМЕННО ДЛЯ ПРОВЕРКИ, КАК ВЫГЛЯДЯТ ТАБЛИЦЫ
    if User.query.count() == 0:
        db.session.add_all([
            User(full_name='Иван Иванов',     role_id=1, email='ivan@example.com',
                 phone='912 473-45-92', user_login='ivan',  is_registered=False),
            User(full_name='Мария Петрова',   role_id=2, email='maria@example.com',
                 phone='912 422-43-65', user_login='maria', is_registered=False),
            User(full_name='Алексей Сидоров', role_id=3, email='alex@example.com',
                 phone='912 901-76-11', user_login='alex',  is_registered=False),
            User(full_name='Ольга Смирнова',  role_id=1, email='olga@example.com',
                 phone='912 111-22-33', user_login='olga',  is_registered=False),
        ])
        db.session.commit()

 # Тестовые подразделения и привязка сотрудников
    if Divisions.query.count() == 0:
        div_dev  = Divisions(div_name='Отдел разработки')
        div_qa   = Divisions(div_name='Отдел тестирования')
        div_an   = Divisions(div_name='Отдел аналитики')
        db.session.add_all([div_dev, div_qa, div_an])
        db.session.commit()

        users = User.query.all()
        # Иванов и Смирнова → Разработка
        db.session.add(UsersAtDivisions(user_id=users[0].id, div_id=div_dev.id))
        db.session.add(UsersAtDivisions(user_id=users[3].id, div_id=div_dev.id))
        # Петрова → Тестирование
        db.session.add(UsersAtDivisions(user_id=users[1].id, div_id=div_qa.id))
        # Сидоров → Аналитика
        db.session.add(UsersAtDivisions(user_id=users[2].id, div_id=div_an.id))
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True)