from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

db = SQLAlchemy()


# ---------- Пользователи для входа ----------
class Registered_Users(UserMixin, db.Model):
    __tablename__ = 'registered_users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def access_level(self):
        user = User.query.filter_by(user_login=self.username).first()
        return user.access_level if user else None


# ---------- Сотрудники ----------
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(24), nullable=False)
    division_id = db.Column(db.String(64), db.ForeignKey('divisions.div_name'), nullable=True)
    access_level = db.Column(db.Integer, nullable=False)
    user_login = db.Column(db.String(32), unique=True, nullable=False)
    is_registered = db.Column(db.Boolean, default=False, nullable=False)
    email = db.Column(db.String(48), nullable=True)
    phone = db.Column(db.String(24), nullable=False)
    
    # Связь с подразделением (через название)
    division = db.relationship('Divisions', backref='users', foreign_keys=[division_id])
    

class Divisions(db.Model):
    __tablename__ = 'divisions'
    id = db.Column(db.Integer, primary_key=True)
    div_name = db.Column(db.String(64), nullable=False, unique=True)  # ← unique=True обязательно!

class UsersAtDivisions(db.Model):
    __tablename__ = 'users_at_divisions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    div_id = db.Column(db.Integer, db.ForeignKey('divisions.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # Связи
    division = db.relationship('Divisions', backref='division_links')
    user = db.relationship('User', backref='division_links')


class UsersAttestations(db.Model):
    __tablename__ = 'users_attestations'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    att_date = db.Column(db.Date)
    valid_until = db.Column(db.Date)
    description = db.Column(db.Text)


class Vacations(db.Model):
    __tablename__ = 'vacations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(32), nullable=False)


class Machines_Property(db.Model):
    __tablename__ = 'machines_property'
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    inventory_num = db.Column(db.Integer, unique=True, nullable=False)
    manufacter_year = db.Column(db.SmallInteger)
    cost = db.Column(db.Float, nullable=False)
    responsible_user_id = db.Column(db.Integer, nullable=False)

class Technical_Maintenance(db.Model):
    __tablename__ = 'technical_maintenance'
    id = db.Column(db.Integer, primary_key=True)
    checked_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(24), nullable=False)
    
    machine_inventory_num = db.Column(     # Добавляем поле для инвентарного номера и указываем его как внешний ключ
        db.Integer, 
        db.ForeignKey('machines_property.inventory_num'), 
        nullable=False
    )
    # В модели Technical_Maintenance
    checked_user = db.relationship('User', foreign_keys=[checked_by])
    machine = db.relationship(     # Настраиваем связь. # Теперь в объекте machine будут доступны все свойства машины (model_name, cost и т.д.)
        'Machines_Property', 
        backref=db.backref('maintenance_records', lazy='dynamic')
    )

class Forces_resources(db.Model):
    __tablename__ = 'forces_resources'
    id = db.Column(db.Integer, primary_key=True)
    division_id = db.Column(db.Integer)
    resource_type = db.Column(db.String(24), nullable=False)
    status = db.Column(db.String(24), nullable=False)