from flask import Blueprint, request, jsonify
from exts import generator
import yaml                                                                  
import os
import requests
import io
import base64
from utils.R import R
from tasks.caculate_similarity import calculate_task 
from flasgger import swag_from
import numpy as np
import cv2
from exts import db
import uuid
from datetime import datetime
import oss2
import config.ossConf as ossConf 
from oss2.credentials import EnvironmentVariableCredentialsProvider
from entity.image_upload import ImageUpload
from entity.task import Tasks


model_bp = Blueprint("pipelineController", __name__, url_prefix="/model/pipeline")


os.environ['OSS_ACCESS_KEY_ID'] = ossConf.OSS_ACCESS_KEY_ID
os.environ['OSS_ACCESS_KEY_SECRET'] = ossConf.OSS_ACCESS_KEY_SECRET

auth = oss2.ProviderAuth(EnvironmentVariableCredentialsProvider())
bucket = oss2.Bucket(auth, ossConf.END_POINT , ossConf.BUCKET_NAME)




@model_bp.route("/uploadAndCalculate", methods=['POST'])
@swag_from('api_doc/get_similarity.yaml')
def uploadAndCalculate():

    file_list = request.files.getlist('image_upload')
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y/%m/%d")



  
    task_ids = []
    # 遍历文件列表中的每个文件
    for file_obj in file_list:
      file_content = file_obj.read()
      

      #上传阿里云操作
      random_uuid = uuid.uuid4()
      random_uuid = str(random_uuid).replace("-", "")[:19]
      new_file_name = f"{random_uuid}_{file_obj.filename}"
      object_name = "image_upload/" + formatted_date + "/" + random_uuid + "/" + new_file_name
      bucket.put_object(object_name, file_content)
      custom_task_id = str(uuid.uuid4())
      
      task=Tasks(id = custom_task_id, status='PROCESSING' ,type='calculate_similarity')

      db.session.add(task)
      db.session.commit()


      #执行异步任务
      result = calculate_task.apply_async(args=(file_content, custom_task_id, random_uuid), task_id=custom_task_id)
      task_id= result.id
      #上传数据库操作
      upload_path = f"https://{ossConf.BUCKET_NAME}.{ossConf.END_POINT}/{object_name}"

      upload = ImageUpload(id = random_uuid, task_id = task_id, path = upload_path)
      db.session.add(upload)
      db.session.commit()

      task_ids.append(task_id)
    return jsonify(
        R.ok().add_data('status','PROCESSING').add_data("calculatSimilarity_ids",task_ids).to_dict()
    ) 
