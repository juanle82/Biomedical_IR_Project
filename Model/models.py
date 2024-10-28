import numpy as np
from Miscellaneous.config import MainConfig


class MainViewModel:
    def __init__(self):
        self._img_vis = np.zeros((10, 10, 3), np.uint8)
        self._img_ir = np.zeros((10, 10, 3), np.uint8)
        self._img_ir_raw = np.zeros((10, 10, 3), np.uint16)
        self._img_ir_processed = np.zeros((10, 10, 3), np.uint8)
        self.config = MainConfig()

    @property
    def img_vis(self):
        return self._img_vis

    @img_vis.setter
    def img_vis(self, value):
        self._img_vis = np.copy(value)

    @property
    def img_ir(self):
        return self._img_ir

    @img_ir.setter
    def img_ir(self, value):
        self._img_ir = np.copy(value)

    @property
    def img_ir_raw(self):
        return self._img_ir_raw

    @img_ir_raw.setter
    def img_ir_raw(self, value):
        self._img_ir_raw = np.copy(value)

    @property
    def img_ir_processed(self):
        return self._img_ir_processed

    @img_ir_processed.setter
    def img_ir_processed(self, value):
        self._img_ir_processed = np.copy(value)
