from celery import current_app as celery
import config.ossConf as ossConf
import oss2
from oss2.credentials import EnvironmentVariableCredentialsProvider
import os
import uuid
from datetime import datetime
from utils.R import R
from utils.preprocess_yaml import extract_contours
import yaml
import io
from utils.feature_extract import get_bitImage_byContours
from flask_cors import CORS, cross_origin
from entity.yaml_upload import Yaml_upload
from entity.yaml_parts import Yaml_parts
from exts import db
from entity.task import Tasks
from flask import current_app as app 
from utils.preprocess_yaml import merge_images
import cv2
import numpy as np
import json

os.environ['OSS_ACCESS_KEY_ID'] = ossConf.OSS_ACCESS_KEY_ID
os.environ['OSS_ACCESS_KEY_SECRET'] = ossConf.OSS_ACCESS_KEY_SECRET

auth = oss2.ProviderAuth(EnvironmentVariableCredentialsProvider())
bucket = oss2.Bucket(auth, ossConf.END_POINT , ossConf.BUCKET_NAME)


# def on_success(task_id):
#   with app.app_context():
#     print('okkkkkkkkkkkkkkkkkkkk',task_id)
#     Tasks.query.filter_by(id=task_id).update({'status': 'FINISHING'})
#     db.session.commit()
#     db.session.close()


@celery.task
def process_yaml(yaml_file, random_uuid, tid):

  with open(yaml_file, 'r') as file:
    data = yaml.load(file, Loader=yaml.FullLoader)

  
  
  filename = yaml_file
  current_date = datetime.now()

  
  # 格式化日期为指定形式的字符串
  formatted_date = current_date.strftime("%Y/%m/%d")

  object_name = "yaml/" + formatted_date + "/" + random_uuid + "/" 
  with open(filename, 'rb') as fileobj:
    bucket.put_object(f"{object_name}{filename}",fileobj)
    

  path=f"https://{ossConf.BUCKET_NAME}.{ossConf.END_POINT}/{object_name+filename}"



  insert_datalist=[]
  image_list=[]


  for i in range(len(data['parts'])):
    contours2, hierarchy2 = extract_contours(data, i)
    #上传特征数据
    contours_data = [contour.tolist() for contour in contours2]
    hierarchy_data = hierarchy2.tolist() if hierarchy2 is not None else []

    json_data = {
        'contours': contours_data,
        'hierarchy': hierarchy_data
    }
    
    

    json_data = json.dumps(json_data)

    bucket.put_object(f"{object_name}images/{i}/features.json", json_data)


    #上传图像数据
    image2 = get_bitImage_byContours(contours2, hierarchy2)
    jpeg_image_stream = io.BytesIO()
    image2.save(jpeg_image_stream, format='JPEG')
    image_data = jpeg_image_stream.getvalue()
    image_path=f"{object_name}images/{i}/{i}.jpg"
    insert_datalist.append({
      'id': str(uuid.uuid4()).replace("-", "")[:19],
      'yaml_id': random_uuid,
      'contours_features': f"https://{ossConf.BUCKET_NAME}.{ossConf.END_POINT}/{object_name}images/{i}/features.json",
      'path': f"https://{ossConf.BUCKET_NAME}.{ossConf.END_POINT}/{image_path}"
    })
    image_list.append(cv2.cvtColor(np.array(image2), cv2.COLOR_BGR2GRAY))
    bucket.put_object(image_path, image_data)




  big_image = merge_images(image_list,desired_size = (800, 800))
  success, preview_image_obj = cv2.imencode(".jpg", big_image)
  preview_image_obj = preview_image_obj.tobytes()
  preview_image_path = f"{object_name}{random_uuid}_preview.jpg"
  bucket.put_object(preview_image_path, preview_image_obj)
  
  yaml_upload= Yaml_upload.query.filter_by(id=random_uuid)


  yaml_upload.update({'preview_path': f"https://{ossConf.BUCKET_NAME}.{ossConf.END_POINT}/{preview_image_path}" ,'path': path,'part_num':len(data['parts'])})
  db.session.commit()


  db.session.bulk_insert_mappings(Yaml_parts, insert_datalist)
  db.session.commit()
  
  os.remove(filename)
  
  Tasks.query.filter_by(id=tid).update({'status': 'FINISHING'})
  db.session.commit()

  

  return path








