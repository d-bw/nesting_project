class R:
    def __init__(self):
        self.success = None
        self.code = None
        self.message = None
        self.data = {}

    @staticmethod
    def ok():
        r = R()
        r.success = True
        r.code = 200  # 这里的200是Python中对应的状态码，你可以根据需要修改
        r.message = "成功"
        return r

    @staticmethod
    def error():
        r = R()
        r.success = False
        r.code = 500  # 这里的500是Python中对应的状态码，你可以根据需要修改
        r.message = "失败"
        return r

    def success(self, success):
        self.success = success
        return self

    def message(self, message):
        self.message = message
        return self

    def code(self, code):
        self.code = code
        return self

    def add_data(self, key=None, value=None, map=None):
        if key and value:
            self.data[key] = value
        elif map:
            self.data = map
        return self

    def to_dict(self):
      if self.data == {}:
        return {
            "success": self.success,
            "code": self.code,
            "message": self.message,
        }

      else:
        return {
            "success": self.success,
            "code": self.code,
            "message": self.message,
            "data": self.data
        }
