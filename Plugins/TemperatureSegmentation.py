from Miscellaneous.PluginBase import PluginBase
import numpy as np
import cv2 as cv
import numpy.typing as npt


class TemperatureSegmentation(PluginBase):
    def __init__(self) -> None:
        name = "Temp. Segmentation"
        is_enable = True
        super().__init__(name, is_enable)

    def ProcessImage(self, img_in: npt.NDArray) -> npt.NDArray:
        img_pre = cv.GaussianBlur(img_in, (5, 5), 0)
        ret3, img_out = cv.threshold(
            img_pre, 0, 65535, cv.THRESH_TOZERO + cv.THRESH_OTSU
        )
        return img_out

    def from_cv16_to_cv8(self, img_in):
        # Transform to uin8_t image for processing with OpenCV
        cv.normalize(img_in, img_in, 0, 65535, cv.NORM_MINMAX)
        np.right_shift(img_in, 8, img_in)
        return cv.applyColorMap(np.uint8(img_in), cv.COLORMAP_HSV)
