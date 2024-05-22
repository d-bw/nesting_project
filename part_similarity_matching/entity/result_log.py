from exts import db
from datetime import datetime

class ResultLog(db.Model):
    __tablename__ = 'result_log'

    id = db.Column(db.String(19), primary_key=True, unique=True, nullable=False)
    yaml_id = db.Column(db.String(19), nullable=False)
    upload_id = db.Column(db.String(19), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    gmt_create = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    gmt_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow , nullable=False)