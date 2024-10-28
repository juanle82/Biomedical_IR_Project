import cv2 as cv
import numpy as np
import numpy.typing as npt

from Miscellaneous.PluginBase import PluginBase


class Contours(PluginBase):
    def __init__(self) -> None:
        name = "Contours detection"
        is_enable = True
        super().__init__(name, is_enable)

    def ProcessImage(self, img_in: npt.NDArray) -> npt.NDArray:
        # Algorithm constants
        reduction_factor = 64
        areaThreshold = 400
        # Apply Otsu threshold
        img_pre = cv.GaussianBlur(img_in, (5, 5), 0)
        _, img_pre = cv.threshold(img_pre, 0, 65535, cv.THRESH_TOZERO + cv.THRESH_OTSU)
        # Convert to a format compatible with OpenCV routines
        cv_img = self.from_cv16_to_cv8(img_in)
        # Get a gray version
        img_pre = self.from_cv16_to_gray(img_pre)
        # Color reduction
        img_pre = img_pre // reduction_factor * reduction_factor + reduction_factor // 2
        # Canny border detection
        img_canny = cv.Canny(img_pre, 50, 70)
        # Dilates an image by using a specific structuring element
        kernel = cv.getStructuringElement(cv.MORPH_RECT, (2, 2))
        img_canny = cv.dilate(img_canny, kernel)
        # Detecting contours
        contours, hierarchy = cv.findContours(
            img_canny, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE
        )
        # Draw contours
        img_contour = np.copy(cv_img)
        # To save largest area
        harea = 0
        htemp = 0
        for idx in range(0, len(contours) - 1):
            contour = contours[idx]
            area = cv.contourArea(contour)
            # Detect small areas
            if area < areaThreshold:
                continue
            # Detect open contours
            if area < cv.arcLength(contour, True):
                continue
            # Get mean temperature
            temp = self.get_area_mean_temp(cv_img, contour)
            # Only draw the highest area with the highest temperature
            if htemp < temp and harea < area:
                harea = area
                to_draw_contour = contour
                to_draw_idx = idx
                htemp = temp
        # Draw temperature of the largest area
        if harea > 0:
            cv.drawContours(
                img_contour,
                contours,
                to_draw_idx,
                (255, 255, 255),
                -1,
                cv.LINE_AA,
                hierarchy,
            )
            # Draw ID for each contour
            temp_str = f"T={htemp} C"
            m = cv.moments(to_draw_contour)
            point = (int(m["m01"] / m["m00"]), int(m["m10"] / m["m00"]))
            self.draw_text(img_contour, temp_str, pos=point)
        return img_contour

    def draw_text(
        self,
        img,
        text,
        font=cv.FONT_HERSHEY_PLAIN,
        pos=(0, 0),
        font_scale=0.5,
        font_thickness=1,
        text_color=(1, 1, 1),
        text_color_bg=(250, 250, 250),
    ):
        x, y = pos
        text_size, _ = cv.getTextSize(text, font, font_scale, font_thickness)
        text_w, text_h = text_size
        cv.rectangle(
            img, (x - 2, y - 2), (x + text_w + 2, y + text_h + 2), text_color_bg, -1
        )
        cv.putText(
            img,
            text,
            (x, y + text_h),
            font,
            font_scale,
            text_color,
            font_thickness,
        )
        return text_size

    def get_area_mean_temp(self, img, contour):
        ROI = cv.boundingRect(contour)
        ImgROI = img[
            int(ROI[1]) : int(ROI[1] + ROI[3]), int(ROI[0]) : int(ROI[0] + ROI[2])
        ]
        # Convert mean radiation value to mean temperature value.
        IR = cv.mean(ImgROI)[0]
        return self.IR_to_temp(IR)

    def IR_to_temp(self, IR_value):
        T1 = 36.0
        T2 = 36.04
        R1 = 8250
        R2 = 8400
        a = (T2 - T1) / (R2 - R1)
        b = T2 - a * R2
        temp = IR_value * (16383.0 / 255) * a + b
        return round(temp, 1)

    def from_cv16_to_cv8(self, img_in):
        # Transform to uin8_t image for processing with OpenCV
        cv.normalize(img_in, img_in, 0, 65535, cv.NORM_MINMAX)
        np.right_shift(img_in, 8, img_in)
        return cv.applyColorMap(np.uint8(img_in), cv.COLORMAP_INFERNO).astype("uint8")

    def from_cv16_to_gray(self, img_in):
        # Transform to uin8_t image for processing with OpenCV
        cv.normalize(img_in, img_in, 0, 65535, cv.NORM_MINMAX)
        np.right_shift(img_in, 8, img_in)
        img_out = cv.merge((np.uint8(img_in), np.uint8(img_in), np.uint8(img_in)))
        return cv.cvtColor(img_out, cv.COLOR_BGR2GRAY)
