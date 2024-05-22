from utils.calculate_similarity import calculate_max_overlapArea, simple_HuMoment 
from utils.preprocess_yaml import extract_contours
from utils.feature_extract import (preprocess_img_byRmBackground,
                    extract_main_object_mask,
                    get_contours_on_image,
                    get_bitImage_byContours)                                   
import os
from exts import generator
from celery import current_app as celery
from exts import db
from entity.yaml_parts import Yaml_parts
from datetime import datetime, timedelta
from entity.yaml_upload import Yaml_upload
from entity.image_upload import ImageUpload
from entity.task import Tasks
import requests
import numpy as np
import urllib.request
from PIL import Image
from io import BytesIO
from oss2.credentials import EnvironmentVariableCredentialsProvider
import oss2
import config.ossConf as ossConf 
import uuid
from entity.result_log import ResultLog
import torch



os.environ['OSS_ACCESS_KEY_ID'] = ossConf.OSS_ACCESS_KEY_ID
os.environ['OSS_ACCESS_KEY_SECRET'] = ossConf.OSS_ACCESS_KEY_SECRET
torch.multiprocessing.set_start_method('spawn', force=True)
auth = oss2.ProviderAuth(EnvironmentVariableCredentialsProvider())
bucket = oss2.Bucket(auth, ossConf.END_POINT , ossConf.BUCKET_NAME)


@celery.task
def calculate_task(raw_image,tid,uid,):
  # # 预处理图像
  preprocessed_image = preprocess_img_byRmBackground(raw_image)
  # 分割模型分割图像物体
  outputs = generator(preprocessed_image, points_per_batch=256)
  
  # 提取主要图物体mask
  main_object_mask = extract_main_object_mask(outputs["masks"])
  # 提取轮廓
  contours1, hierarchy1 = get_contours_on_image(main_object_mask)
  # 通过轮廓渲染为灰度图
  image1 = get_bitImage_byContours(contours1, hierarchy1)
  similarity = []
  images = []
  yaml_ids = []
  

  today_start = datetime.combine(datetime.today(), datetime.min.time())
  today_end = today_start + timedelta(days=1)

  

  # 查询当天的数据
  todays_yaml_uploads = db.session.query(Yaml_upload, Tasks).join(
      Tasks, Yaml_upload.task_id == Tasks.id
  ).filter(
      Yaml_upload.gmt_create >= today_start,
      Yaml_upload.gmt_create < today_end,
      Tasks.status == "FINISHING"
  ).all()
  result_ids = [
    yaml_upload.id for yaml_upload, task in todays_yaml_uploads 
    ]
  print(result_ids)

  yaml_parts = Yaml_parts.query.filter(Yaml_parts.yaml_id.in_(result_ids)).all()
  result = [
    {
        "yaml_id": part.yaml_id,
        "contours_features": part.contours_features,
        "path": part.path,
    } for part in yaml_parts
  ]

  #imageUpload = ImageUpload.query.filter_by(id=image_id)

  for part in result:
    #处理图形与json格式
    features = part["contours_features"]
    features = requests.get(features).json()
    contours2 = features['contours']
    hierarchy2 = features['hierarchy']
    image2 = part["path"]
    urllib.request.urlretrieve(image2,"yaml_image.jpg")
    image2 = Image.open("yaml_image.jpg")

    contours2 = [np.array(contour, dtype=np.int32) for contour in contours2]
    hierarchy2 = np.array(hierarchy2, dtype=np.int32) if hierarchy2 else None

    #相似度计算
    _, ratio = calculate_max_overlapArea(contours1, contours2, hierarchy1, hierarchy2, image1, image2)
    similarity.append(ratio)
    images.append(image2)
    yaml_ids.append(part["yaml_id"])



  combined = sorted(zip(similarity, images,yaml_ids), reverse=True)
    
  similarity = [tup[0] for tup in combined][0:10]
  images = [tup[1] for tup in combined][0:10]
  yamls = [tup[2] for tup in combined][0:10]

  current_date = datetime.now()
  formatted_date = current_date.strftime("%Y/%m/%d")
  insert_datalist = []
  #上传oss以及数据库
  for idx, img, yaml_id in enumerate(zip(images,yamls)):
    # 将 PIL 图像转换为字节流
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()
    
    # 定义在 OSS 上的文件名
    random_uuid = uuid.uuid4()
    random_uuid = str(random_uuid).replace("-", "")[:19]
    filename = f'result_{idx+1}.jpg'
    object_name = "image_upload/" + formatted_date + "/" + random_uuid + "/" + filename
    # 上传图像
    bucket.put_object(object_name, img_byte_arr)
    insert_datalist.append({
      'id': random_uuid,
      'yaml_id': yaml_id,
      'uplaod_id': uid,
      'path': f"https://{ossConf.BUCKET_NAME}.{ossConf.END_POINT}/{object_name}"
    })


  db.session.bulk_insert_mappings(ResultLog, insert_datalist)
  db.session.commit()
  Tasks.query.filter_by(id=tid).update({'status': 'FINISHING'})
  db.session.commit()
  
  db.session.close()

  


  












