from flask import Blueprint, request, jsonify
from flasgger import swag_from
from utils.R import R
from tasks.preprocess_yaml import process_yaml
from celery.result import AsyncResult
import os
from entity.task import Tasks
from exts import db
import uuid
from datetime import datetime
import oss2
from oss2.credentials import EnvironmentVariableCredentialsProvider
import config.ossConf as ossConf 
from entity.yaml_upload import Yaml_upload
import yaml



oss_bp = Blueprint("ossController", __name__, url_prefix="/model/preprocess")

os.environ['OSS_ACCESS_KEY_ID'] = ossConf.OSS_ACCESS_KEY_ID
os.environ['OSS_ACCESS_KEY_SECRET'] = ossConf.OSS_ACCESS_KEY_SECRET

auth = oss2.ProviderAuth(EnvironmentVariableCredentialsProvider())
bucket = oss2.Bucket(auth, ossConf.END_POINT , ossConf.BUCKET_NAME)



@oss_bp.route("/uploadYaml", methods=['POST'])
@swag_from('api_doc/oss.yaml')
def uploadYaml():

  yaml_file = request.files['upload_yaml']
  
  random_uuid = uuid.uuid4()
  random_uuid = str(random_uuid).replace("-", "")[:19]
  filename = f"{random_uuid}{yaml_file.filename}"
  yaml_file.save(filename)
  custom_task_id = str(uuid.uuid4())
      
  task=Tasks(id = custom_task_id, status='PROCESSING' ,type='process_yaml')



  db.session.add(task)
  db.session.commit()


  result = process_yaml.apply_async(args=(filename, random_uuid, custom_task_id),task_id = custom_task_id)

  

  task_id= result.id

  new_yaml=Yaml_upload(id = random_uuid, task_id=task_id)
  db.session.add(new_yaml)
  db.session.commit()



  return jsonify(
      R.ok().add_data('status','PROCESSING').add_data("processYaml_id",task_id).to_dict()
  )    


@oss_bp.route("/oss_status", methods=['POST'])
def getStatus():
  task_id = request.args.get('process_upload_id')
  result = AsyncResult(task_id)
  if result.ready():
    path = result.get()
    return jsonify(
        R.ok().add_data('status','FINISHING').add_data('source_path',path).to_dict()
      )
  else:
    return jsonify(
        R.ok().add_data('status','PROCESSING').add_data("processYaml_id",task_id).to_dict()
    ) 




