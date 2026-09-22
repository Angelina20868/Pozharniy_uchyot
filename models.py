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


# ---------- Сотрудники ----------
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    role_id = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(24), nullable=False)
    user_login = db.Column(db.String(80), unique=True, nullable=True)
    is_registered = db.Column(db.Boolean, default=False, nullable=False)


class Divisions(db.Model):
    __tablename__ = 'divisions'
    id = db.Column(db.Integer, primary_key=True)
    div_name = db.Column(db.String(100), nullable=False)


class UsersAtDivisions(db.Model):
    __tablename__ = 'users_at_divisions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    div_id = db.Column(db.Integer, db.ForeignKey('divisions.id'))


class Attestations(db.Model):
    __tablename__ = 'attestations'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(32), nullable=False)


class UsersAttestations(db.Model):
    __tablename__ = 'users_attestations'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    att_id = db.Column(db.Integer, db.ForeignKey('attestations.id'))
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
    category = db.Column(db.String(100), nullable=False)
    manufacter_year = db.Column(db.SmallInteger)
    cost = db.Column(db.Float, nullable=False)
    responsible_user_id = db.Column(db.Integer, nullable=False)


class Technical_Maintenance(db.Model):
    __tablename__ = 'technical_maintenance'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    resource_id = db.Column(db.Integer, nullable=False)
    checked_by = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(24), nullable=False)


class Forces_resources(db.Model):
    __tablename__ = 'forces_resources'
    id = db.Column(db.Integer, primary_key=True)
    division_id = db.Column(db.Integer)
    resource_type = db.Column(db.String(24), nullable=False)
    status = db.Column(db.String(24), nullable=False)