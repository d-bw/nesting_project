from exts import db
from datetime import datetime

class Yaml_parts(db.Model):
    __tablename__ = 'yaml_parts'

    id = db.Column(db.String(19), primary_key=True, unique=True, nullable=False)
    yaml_id = db.Column(db.String(19),nullable=False)
    contours_features = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    gmt_create = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    gmt_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow , nullable=False)
