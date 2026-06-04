from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    approval_requested = db.Column(db.Boolean, default=False)
    approval_requested_at = db.Column(db.DateTime, nullable=True)
    llm_model = db.Column(db.String(100), nullable=True)
    llm_api_key = db.Column(db.String(512), nullable=True)
    llm_base_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    records = db.relationship('AnalysisRecord', backref='user', lazy='dynamic')


class AnalysisRecord(db.Model):
    __tablename__ = 'analysis_records'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    module_type = db.Column(db.String(50), nullable=False)
    input_text = db.Column(db.Text, nullable=True)
    result_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
