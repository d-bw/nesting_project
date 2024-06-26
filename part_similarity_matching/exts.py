from transformers import pipeline
import torch
from flask_sqlalchemy import SQLAlchemy
from celery import Celery




#模型引用
device = "cuda" if torch.cuda.is_available() else "cpu"
generator = pipeline("mask-generation", model="facebook/sam-vit-huge", device=device, points_per_batch=256)
#数据库引用
db = SQLAlchemy()


def init_celery(app):
  celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'], backend=app.config['CELERY_RESULT_BACKEND'])
  celery.conf.update(app.config)
  TaskBase = celery.Task
    
  class ContextTask(TaskBase):
      abstract = True
      def __call__(self, *args, **kwargs):
          with app.app_context():
              return TaskBase.__call__(self, *args, **kwargs)

  celery.Task = ContextTask
  return celery



