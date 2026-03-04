"""
Database models for Plant Chap
All models are user-scoped for multi-user support
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from datetime import datetime

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    crops = db.relationship('Crop', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'

class Crop(db.Model):
    """Crop model - users can have multiple grows"""
    __tablename__ = 'crops'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    strain = db.Column(db.String(100))
    medium = db.Column(db.String(100))  # soil, coco, hydro, etc.
    grow_space = db.Column(db.String(100))  # tent size, room, outdoor
    date_planted = db.Column(db.DateTime)
    date_flipped = db.Column(db.DateTime)
    harvest_date = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='vegetative')  # seedling, vegetative, flowering, drying, curing, harvested
    photo = db.Column(db.String(255))
    strain_description = db.Column(db.Text)
    strain_type = db.Column(db.String(50))
    strain_lineage = db.Column(db.String(200))
    strain_lineage_tree = db.Column(db.Text)  # JSON: full lineage tree from seedfinder
    strain_breeder = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    plant_parameters = db.relationship('PlantParameter', backref='crop', lazy=True, cascade='all, delete-orphan')
    grow_logs = db.relationship('GrowLog', backref='crop', lazy=True, cascade='all, delete-orphan')
    scheduled_tasks = db.relationship('ScheduledTask', backref='crop', lazy=True, cascade='all, delete-orphan')
    amendments = db.relationship('Amendment', backref='crop', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Crop {self.name} (User: {self.user_id})>'

class PlantParameter(db.Model):
    """Plant parameter readings"""
    __tablename__ = 'plant_parameters'
    
    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, db.ForeignKey('crops.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    ph_runoff = db.Column(db.Float)
    ph_feed = db.Column(db.Float)
    ec_ppm = db.Column(db.Float)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    light_hours = db.Column(db.Float)
    vpd = db.Column(db.Float)
    ppfd = db.Column(db.Float)
    water_mbars = db.Column(db.Float)
    notes = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'crop_id': self.crop_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'ph_runoff': self.ph_runoff,
            'ph_feed': self.ph_feed,
            'ec_ppm': self.ec_ppm,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'light_hours': self.light_hours,
            'vpd': self.vpd,
            'ppfd': self.ppfd,
            'water_mbars': self.water_mbars,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<PlantParameter {self.id} (Crop: {self.crop_id})>'

class GrowLog(db.Model):
    """Grow log entries"""
    __tablename__ = 'grow_log'
    
    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, db.ForeignKey('crops.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    task_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=True, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'crop_id': self.crop_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'task_type': self.task_type,
            'description': self.description,
            'completed': self.completed
        }
    
    def __repr__(self):
        return f'<GrowLog {self.id} (Crop: {self.crop_id})>'

class ScheduledTask(db.Model):
    """Scheduled tasks (feeding, watering, etc.)"""
    __tablename__ = 'scheduled_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, db.ForeignKey('crops.id'), nullable=False, index=True)
    task_name = db.Column(db.String(100), nullable=False)
    frequency_days = db.Column(db.Integer)
    last_completed = db.Column(db.DateTime)
    next_due = db.Column(db.DateTime, index=True)
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True, nullable=False)
    is_recurring = db.Column(db.Boolean, default=True, nullable=False)
    specific_date = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'crop_id': self.crop_id,
            'task_name': self.task_name,
            'frequency_days': self.frequency_days,
            'last_completed': self.last_completed.isoformat() if self.last_completed else None,
            'next_due': self.next_due.isoformat() if self.next_due else None,
            'description': self.description,
            'active': self.active,
            'is_recurring': self.is_recurring,
            'specific_date': self.specific_date.isoformat() if self.specific_date else None
        }
    
    def __repr__(self):
        return f'<ScheduledTask {self.task_name} (Crop: {self.crop_id})>'

class Amendment(db.Model):
    """Amendments and nutrients tracking"""
    __tablename__ = 'amendments'
    
    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, db.ForeignKey('crops.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50))  # nutrient, soil, supplement, pesticide
    amount = db.Column(db.Float)
    unit = db.Column(db.String(30))  # ml, g, tsp, tbsp, etc.
    date_applied = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'crop_id': self.crop_id,
            'name': self.name,
            'type': self.type,
            'amount': self.amount,
            'unit': self.unit,
            'date_applied': self.date_applied.isoformat() if self.date_applied else None,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<Amendment {self.name} (Crop: {self.crop_id})>'
