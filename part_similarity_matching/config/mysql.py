class BaseConfig(object):

    # 数据库的配置
    DIALCT = "mysql"
    DRITVER = "pymysql"
    HOST = '0.tcp.ap.ngrok.io'
    PORT = "10974"
    USERNAME = "root"
    PASSWORD = "qwe197344"
    DBNAME = 'part_similarity_matching'

    SQLALCHEMY_DATABASE_URI = f"{DIALCT}+{DRITVER}://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?charset=utf8"
    SQLALCHEMY_TRACK_MODIFICATIONS = True