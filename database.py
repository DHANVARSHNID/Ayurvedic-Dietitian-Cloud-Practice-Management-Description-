from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Patient Table
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # Ayurveda-specific fields
    prakriti = db.Column(db.String(50))    # Vata, Pitta, Kapha
    agni = db.Column(db.String(50))        # Mandagni, Tikshnagni, Vishamagni, Samagni
    ama = db.Column(db.String(50))         # Yes/No or levels
    allergy = db.Column(db.String(200))    # Optional allergies

    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
