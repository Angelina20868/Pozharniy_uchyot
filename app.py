from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

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
    # Передаём список карточек в шаблон (чтобы не дублировать HTML)
    #вот это все надо пропихнуть в index.html
    cards = [
        {"title": "Личный кабинет",
         "image": "12.jpg", #замени на статичные пути типа ./12.jpg //проверь как пути указываются, если картинки в статике лежат
         #я просто не помню, вроде там будет ./static/images/твоя_картинка.jpg
         "text": '<a href="#" class="text-decoration-none">Справка 2-НДФЛ (заказ)</a><br>'
            '<a href="#" class="text-decoration-none">Справка о доходах</a><br>'
            '<a href="#" class="text-decoration-none">Справка с места работы</a><br>'
            '<a href="#" class="text-decoration-none">Заказ пропусков</a><br>'
            '<a href="#" class="text-decoration-none">Мои отпуска</a><br>'
            '<a href="#" class="text-decoration-none">Контакты коллег</a>'
        },
        {"title": "Кадры",
         "image": "13.jpg",
         "text": '<a href="#" class="text-decoration-none">Аттестация спасателей</a><br>'
            '<a href="#" class="text-decoration-none">Электронная папка №21</a><br>'
            '<a href="#" class="text-decoration-none">Электронная папка №22</a><br>'
            '<a href="#" class="text-decoration-none">Электронная папка №23</a><br>'
            '<a href="#" class="text-decoration-none">Электронная папка №24</a><br>'
            '<a href="#" class="text-decoration-none">Электронная папка №25</a>',
        },
        {"title": "Штаб",
         "image": "12.jpg",
         "text": '<a href="#" class="text-decoration-none">Расчёты по тактике</a><br>'
            '<a href="#" class="text-decoration-none">Учёт сил и средств</a><br>'
            '<a href="#" class="text-decoration-none">Отделения (старшие)</a><br>'
            '&nbsp;<br>'
            '&nbsp;<br>'
            '&nbsp;<br>',
        },
        {"title": "Нормативная база",
         "image": "12.jpg",
         "text":'<a href="https://18.mchs.gov.ru/documents/ukazy-prezidenta-rf" class="text-decoration-none">Указы президента РФ</a><br>'
            '<a href="https://18.mchs.gov.ru/documents/federalnye-konstitucionnye-zakony" class="text-decoration-none">Федеральные законы</a><br>'
            '<a href="https://18.mchs.gov.ru/documents/postanovleniya-pravitelstva-rf" class="text-decoration-none">Постановления правительства РФ</a><br>'
            '<a href="#" class="text-decoration-none">Устав караула</a><br>'
            '&nbsp;<br>'
            '&nbsp;<br>',
        },
        {"title": "Электронные журналы",
         "image": "12.jpg",
         "text": '<a href="#" class="text-decoration-none">Расписание дежурств</a><br>'
            '<a href="#" class="text-decoration-none">Журнал ТО техники</a><br>'
            '<a href="#" class="text-decoration-none">Журнал инструктажей</a><br>'
            '&nbsp;<br>'
            '&nbsp;<br>'
            '&nbsp;<br>',
        },
        {"title": "Информация",
         "image": "13.jpg",
         "text":'<a href="#" class="text-decoration-none">Приказы по части</a><br>'
            '<a href="#" class="text-decoration-none">Распоряжения</a><br>'
            '<a href="#" class="text-decoration-none">Объявления</a><br>'
            '&nbsp;<br>'
            '&nbsp;<br>'
            '&nbsp;<br>',
        }
    ]
    #вот до этого момента
    return render_template('index.html', cards=cards)#cards = cards тебе уже не нужны будут тогда

@app.route('/objects/<table_name>')
def objects(table_name):
     # --- Специальная обработка для подразделений ---
    if table_name == 'divisions':
        divisions = Divisions.query.all()
        divisions_with_users = []
        for div in divisions:
            # Находим всех сотрудников, привязанных к этому подразделению
            users = (User.query
                     .join(UsersAtDivisions, UsersAtDivisions.user_id == User.id)
                     .filter(UsersAtDivisions.div_id == div.id)
                     .all())
            divisions_with_users.append({
                'division': div,
                'users': users
            })
        return render_template('divisions.html',
                               divisions_with_users=divisions_with_users)

    # --- Универсальная обработка для остальных таблиц ---
    table_map = {
        'user': User,
        'machines_property': Machines_Property,
        'technical_maintenance': Technical_Maintenance,
        'attestations': Attestations,
        'usersAttestations': UsersAttestations,
        'usersAtDivisions': UsersAtDivisions,
        'vacations': Vacations,
        'forces_resources': Forces_resources
    }
    if table_name not in table_map:
        return "Таблица не найдена", 404

    model = table_map[table_name]

    # Специальная обработка для таблицы связей «сотрудник ↔ подразделение»
    if table_name == 'usersAtDivisions':
        rows = []
        for link in model.query.all():   # ← запрашиваем напрямую, без items
            rows.append({
                'id': link.id,
                'full_name': link.user.full_name if link.user else '—',
                'div_name': link.division.div_name if link.division else '—',
            })
        return render_template('users_at_divisions.html', rows=rows)

    items = model.query.all()
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
