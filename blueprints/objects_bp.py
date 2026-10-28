from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from sqlalchemy import select, func, outerjoin
from collections import defaultdict
from datetime import datetime
from models import (
    db, User, Divisions, UsersAtDivisions, UsersAttestations, 
    Vacations, Machines_Property, Technical_Maintenance, Forces_resources
)

objects_bp = Blueprint('objects', __name__, url_prefix='/objects')

# Маппинг имён таблиц на модели
TABLE_MAP = {
    'user': User, 'machines_property': Machines_Property,
    'technical_maintenance': Technical_Maintenance,
    'usersAttestations': UsersAttestations, 'divisions': Divisions,
    'usersAtDivisions': UsersAtDivisions, 'vacations': Vacations,
    'forces_resources': Forces_resources,
}

# Какие access_level могут редактировать каждую таблицу
EDIT_PERMISSIONS = {
    'user': [1, 2], 'machines_property': [1, 2], 'technical_maintenance': [1, 2],
    'attestations': [1, 2], 'usersAttestations': [1, 2], 'divisions': [1],
    'usersAtDivisions': [1], 'vacations': [1, 2, 3], 'forces_resources': [1, 2],
}

def can_edit(table_name):
    """Проверяет, имеет ли текущий пользователь право редактировать таблицу."""
    if not current_user.is_authenticated:
        return False
    access = current_user.access_level
    return access in EDIT_PERMISSIONS.get(table_name, [])

@objects_bp.route('/maintenance')
def show_maintenance():
    # Получаем данные из БД одним запросом (чтобы избежать проблемы N+1)
    records = db.session.query(Technical_Maintenance).all()
    
    # Передаем список записей в HTML-шаблон под именем 'maintenance_records'
    return render_template('maintenance.html', maintenance_records=records)

@objects_bp.route('/<table_name>')
@login_required
def objects(table_name):
    if table_name not in TABLE_MAP:
        return "Таблица не найдена", 404
    
    model = TABLE_MAP[table_name]
    
    editable = can_edit(table_name)

    # ===== Специальная обработка: подразделения + сотрудники =====
    if table_name == 'usersAtDivisions':
        
        # ---------------------------------------------------------
        # ЗАПРОС 1: Подсчёт сотрудников по подразделениям
        # SQL-эквивалент:
        #   SELECT divisions.id, divisions.div_name, COUNT(user.id) AS user_count
        #   FROM divisions
        #   LEFT JOIN user ON user.division_id = divisions.div_name
        #   GROUP BY divisions.id, divisions.div_name
        # ---------------------------------------------------------
        stmt_count = (
            select(
                Divisions.id,
                Divisions.div_name,
                func.count(User.id).label('user_count')
            )
            .outerjoin(User, func.lower(User.division_id) == func.lower(Divisions.div_name))
            .group_by(Divisions.id, Divisions.div_name)
            .order_by(Divisions.id)
        )
        stats = db.session.execute(stmt_count).all()
        
        # ---------------------------------------------------------
        # ЗАПРОС 2: Список сотрудников с подразделениями
        # SQL-эквивалент:
        #   SELECT divisions.*, user.*
        #   FROM divisions
        #   LEFT JOIN user ON user.division_id = divisions.div_name
        #   ORDER BY divisions.id, user.full_name
        # ---------------------------------------------------------
        stmt_rows = (
            select(Divisions, User)
            .outerjoin(User, func.lower(User.division_id) == func.lower(Divisions.div_name))
            .order_by(Divisions.id, User.full_name)
        )
        rows = db.session.execute(stmt_rows).all()
        
        # Группируем результат по подразделениям
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
        
        # Подставляем счётчики из GROUP BY
        for row in stats:
            divisions_data[row.id]['user_count'] = row.user_count
        
        return render_template('users_at_divisions.html',
                               divisions_data=divisions_data.values(),
                               can_edit=editable)
    
    # ===== Остальные таблицы: обычный SELECT * FROM table =====
    # Эквивалент SQL: SELECT * FROM <table>
    stmt = select(model)
    items = db.session.execute(stmt).scalars().all()
    columns = [col.name for col in model.__table__.columns if col.name != 'id']

    # ВАЖНО: передаем can_edit в шаблон!
    return render_template('objects.html',
                           table_name=table_name,
                           items=items,
                           columns=columns,
                           can_edit=can_edit(table_name)) # <--- ДОБАВЛЕНО

# --- ФУНКЦИИ CRUD (ДОБАВЛЕНО, ЧТОБЫ ШАБЛОН НЕ ПАДАЛ) ---

@objects_bp.route('/<table_name>/add', methods=['GET', 'POST'])
@login_required
def add_item(table_name):
    if table_name not in TABLE_MAP or not can_edit(table_name):
        flash('Нет прав или таблица не найдена', 'danger')
        return redirect(url_for('main.index'))
    
    model = TABLE_MAP[table_name]
    if request.method == 'POST':
        new_item = model()
        for col in model.__table__.columns:
            if col.name != 'id' and col.name in request.form:
                setattr(new_item, col.name, _coerce_value(col, request.form[col.name]))
        db.session.add(new_item)
        db.session.commit()
        flash('Запись добавлена', 'success')
        return redirect(url_for('objects.objects', table_name=table_name))
        
    return render_template(
        'edit_item.html',
        table_name=table_name,
        item=None,
        columns=model.__table__.columns,
        html_input_type=_html_input_type,   # <--- передаём функцию
        is_new=True                          # <--- заодно исправьте is_new
    )   
@objects_bp.route('/<table_name>/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(table_name, item_id):
    if table_name not in TABLE_MAP or not can_edit(table_name):
        flash('Нет прав или таблица не найдена', 'danger')
        return redirect(url_for('main.index'))
        
    model = TABLE_MAP[table_name]
    item = db.session.get(model, item_id)
    if not item:
        flash('Запись не найдена', 'warning')
        return redirect(url_for('objects.objects', table_name=table_name))

    if request.method == 'POST':
        for col in model.__table__.columns:
            if col.name != 'id' and col.name in request.form:
                setattr(item, col.name, _coerce_value(col, request.form[col.name]))
        db.session.commit()
        flash('Запись обновлена', 'success')
        return redirect(url_for('objects.objects', table_name=table_name))

    return render_template(
        'edit_item.html',
        table_name=table_name,
        item=item,
        columns=model.__table__.columns,
        html_input_type=_html_input_type,
        is_new=False
    )

@objects_bp.route('/<table_name>/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_item(table_name, item_id):
    if table_name not in TABLE_MAP or not can_edit(table_name):
        flash('У вас нет прав для удаления.', 'danger')
        return redirect(url_for('objects.objects', table_name=table_name))
        
    model = TABLE_MAP[table_name]
    item = db.session.get(model, item_id)
    if item:
        try:
            db.session.delete(item)
            db.session.commit()
            flash('Запись удалена.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при удалении: {e}', 'danger')
    return redirect(url_for('objects.objects', table_name=table_name))

# --- Вспомогательные функции ---
def _coerce_value(column, raw_value):
    if raw_value == '' or raw_value is None: return None
    col_type = column.type
    if isinstance(col_type, db.Integer) or isinstance(col_type, db.SmallInteger): return int(raw_value)
    if isinstance(col_type, db.Float): return float(raw_value)
    if isinstance(col_type, db.Boolean): return raw_value.lower() in ('1', 'true', 'on', 'yes')
    if isinstance(col_type, db.Date): return datetime.strptime(raw_value, '%Y-%m-%d').date()
    return raw_value

def _html_input_type(column):
    """Подбирает type для <input> на основе типа колонки."""
    col_type = column.type
    if isinstance(col_type, db.Date):
        return 'date'
    if isinstance(col_type, (db.Integer, db.SmallInteger)):
        return 'number'
    if isinstance(col_type, db.Float):
        return 'number'
    if isinstance(col_type, db.Boolean):
        return 'checkbox'
    return 'text'