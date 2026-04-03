from datetime import datetime
from models.db import db


class Claim(db.Model):
    __tablename__ = "claims"

    id = db.Column(db.Integer, primary_key=True)

    # Numéro unique du ticket
    ticket_number = db.Column(db.String(30), unique=True, nullable=False)

    # Informations patient
    patient_name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(30), nullable=True)

    # Attribution intelligente
    service = db.Column(db.String(100), default="Consultation")
    priority = db.Column(db.String(50), default="Normale")

    # Réclamation
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

    # Suivi
    status = db.Column(db.String(30), default="En attente")
    assigned_agent = db.Column(db.String(120), default="Non assigné")

    # 📦 Archivage automatique
    is_archived = db.Column(db.Boolean, default=False)

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<Claim {self.ticket_number} - {self.patient_name}>"