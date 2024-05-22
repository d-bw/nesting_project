from flask import Flask
from flasgger import Swagger
from controller.pipelineController import model_bp
from controller.ossController import oss_bp
from flask_cors import CORS
#form exts import init_celery
from exts import db
from config.mysql import BaseConfig
from exts import init_celery
import threading
import torch


app = Flask(__name__)
torch.multiprocessing.set_start_method('spawn', force=True)
#加载数据库
app.config.from_object(BaseConfig)
app.config['CELERY_BROKER_URL'] = 'amqp://guest:guest@localhost:5672//'
app.config['CELERY_RESULT_BACKEND'] = 'rpc://'




db.init_app(app)

swagger = Swagger(app)




app.register_blueprint(model_bp)
app.register_blueprint(oss_bp)

CORS(app)

celery = init_celery(app)
def start_celery_worker():
    
    celery.worker_main(['worker', '--loglevel=info'])

# 启动 Celery worker
celery_worker_thread = threading.Thread(target=start_celery_worker)
celery_worker_thread.start()


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


if __name__ == '__main__':
    
    app.run()
