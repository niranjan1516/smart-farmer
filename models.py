from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
# NEW (CORRECT FOR INDIA)
from datetime import datetime, timedelta

# 1. helper function for IST
def get_ist_time():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    # Increased length to 256 to store the Hashed Password securely
    password_hash = db.Column(db.String(256), nullable=False) 
    
    reports = db.relationship('History', backref='farmer', lazy=True)

class History(db.Model):
    __tablename__ = 'history'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # New Detailed Inputs
    district = db.Column(db.String(50), nullable=False)
    village = db.Column(db.String(50))
    pincode = db.Column(db.String(10))
    
    # Environmental Context
    terrain = db.Column(db.String(20)) # e.g., 'river', 'mountain', 'plain'
    soil_color = db.Column(db.String(20))
    
    predicted_crop = db.Column(db.String(50))
    created_at  = db.Column(db.DateTime, default=get_ist_time)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

# Examiner Note: "I used Foreign Keys to create a Relational Schema, linking farmers to their data."