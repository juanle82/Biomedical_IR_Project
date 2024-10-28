import numpy as np
import numpy.typing as npt


class PluginBase:
    def __init__(self, name: str, is_enable=True) -> None:
        self.name = name
        self.is_enable = is_enable

    def ProcessImage(self, img_in: npt.NDArray) -> npt.NDArray:
        return img_in
