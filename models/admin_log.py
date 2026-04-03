from datetime import datetime
from models.db import db

class AdminLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)