from Miscellaneous.PluginBase import PluginBase
import numpy as np
import cv2 as cv
import numpy.typing as npt


class FaceDetection(PluginBase):
    def __init__(self) -> None:
        name = "Face detection"
        is_enable = True
        super().__init__(name, is_enable)
        # Load the cascade
        self.face_cascade = cv.CascadeClassifier(
            cv.data.haarcascades + "haarcascade_frontalface_alt2.xml"
        )

    def ProcessImage(self, img_in: npt.NDArray) -> npt.NDArray:
        # Convert to a format compatible with OpenCV routines
        cv_img = self.from_cv16_to_gray(img_in)
        # Detect the faces
        faces = self.face_cascade.detectMultiScale(
            cv_img,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(10, 10),
            flags=cv.CASCADE_SCALE_IMAGE,
        )
        # Draw the rectangle around each face
        for (x, y, w, h) in faces:
            cv.rectangle(img_in, (x, y), (x + w, y + h), (255, 0, 0), 2)
            temp = self.get_mean_temp(img_in, (x, y, w, h))
            self.draw_text(img_in, f"T={temp} C", pos=(x, y))
        return img_in

    def get_mean_temp(self, img, ROI):
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

    def from_cv16_to_gray(self, img_in):
        # Transform to uin8_t image for processing with OpenCV
        cv.normalize(img_in, img_in, 0, 65535, cv.NORM_MINMAX)
        np.right_shift(img_in, 8, img_in)
        img_out = cv.merge((np.uint8(img_in), np.uint8(img_in), np.uint8(img_in)))
        return cv.cvtColor(img_out, cv.COLOR_BGR2GRAY)

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
        cv.rectangle(img, (x - 2, y - 2 - text_h), (x + text_w, y), text_color_bg, -1)
        cv.putText(
            img,
            text,
            (x, y),
            font,
            font_scale,
            text_color,
            font_thickness,
        )
        return text_size
