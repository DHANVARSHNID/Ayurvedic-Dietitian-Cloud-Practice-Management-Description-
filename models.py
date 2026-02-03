from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Patient(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))
    dosha = db.Column(db.String(10))

class DietPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    food_item = db.Column(db.String(100))
    quantity = db.Column(db.String(50))
    time_slot = db.Column(db.String(50))

class MealLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    meal_file = db.Column(db.String(200))
    calories = db.Column(db.Float)
    date = db.Column(db.Date)

