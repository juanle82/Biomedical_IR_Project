import os
import sys
import yaml


class Dict2Class(object):
    def __init__(self, my_dict):
        for key in my_dict:
            if type(my_dict[key]) is dict:
                setattr(self, key, Dict2Class(my_dict[key]))
            else:
                setattr(self, key, my_dict[key])


class MainConfig:
    def __init__(self):
        config = Config()
        Dict2Class.__init__(self, config.value["APP"])


class ViewConfig:
    def __init__(self):
        config = Config()
        Dict2Class.__init__(self, config.value["VIEW"])


class CameraConfig(Dict2Class):
    def __init__(self):
        config = Config()
        Dict2Class.__init__(self, config.value["CAMERAS"])


class Config:
    def __init__(self):
        if getattr(sys, "frozen", False):
            path = os.path.dirname(sys.executable)
            path = os.path.join(path, "config.yaml")
            if not os.path.exists(path):
                path = sys._MEIPASS
                path = os.path.join(path, "config.yaml")
        else:
            path = "./config.yaml"
        self.value = self.__loadConfig(path)

    def __loadConfig(self, file_path):
        with open(file_path, "r") as f:
            return yaml.safe_load(f)
