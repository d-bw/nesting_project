from exts import db
from datetime import datetime

class Tasks(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.String(36), primary_key=True)
    status = db.Column(db.String(255))
    type = db.Column(db.String(255))
    gmt_create = db.Column(db.DateTime, default=datetime.utcnow)
    gmt_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
