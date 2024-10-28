import time
import math
import logging
import numpy as np
import cv2 as cv
from Miscellaneous.config import CameraConfig
from queue import Queue
from Miscellaneous.uvctypes import *
from picamera2 import Picamera2
from threading import Lock


class Camera:
    # def __init__(self, name, w, h, detectCam):
    def __init__(self, name, w, h):
        self.name = name
        self.resolution = (w, h)
        self.idx = 0
        self.dev = None
        self.is_open = False
        self.logger = logging.getLogger(__name__)

    def get_dev(self):
        pass

    def open(self):
        pass

    def close(self):
        pass

    def capture(self):
        pass


class CameraVIS(Camera):

    INDEX_MAX = 50

    def __init__(self):
        self.config = CameraConfig()
        Camera.__init__(
            self,
            "VIS",
            self.config.VISIBLE.resolution.x,
            self.config.VISIBLE.resolution.y,
        )
        self.capture_resolution = (
            self.config.VISIBLE.capture_resolution.x,
            self.config.VISIBLE.capture_resolution.y,
        )
        # Logic
        self.lock = Lock()
        # Configuring the device
        self.dev = Picamera2()
        self.high_res_config = self.dev.create_preview_configuration(
            main={"size": self.capture_resolution}
        )
        self.preview_config = self.dev.create_preview_configuration(
            main={"size": self.resolution}
        )

    def open(self):
        self.dev.configure(self.preview_config)
        self.dev.start()
        return 0

    def close(self):
        if self.dev.started:
            self.dev.stop()

    def capture(self):
        return self.__get_image(self.resolution)

    def take_photo(self):
        ret = 0
        frame = self.dev.switch_mode_and_capture_array(self.high_res_config)
        return ret, frame

    def __get_image(self, resolution):
        with self.lock:
            # The size of the output array should have a multiple of 16 for height and 32 for width
            if self.dev is not None:
                frame = self.dev.capture_array()
                # After capture, crop the array to the setted resolution
                frame = frame[: resolution[1], : resolution[0]]
            else:
                frame = None
            return True, frame

    def configure(self, resolution=None, framerate=None):
        if self.dev is not None:
            if resolution is None:
                self.dev.resolution = self.resolution
                self.dev.framerate = 30
            else:
                self.dev.resolution = resolution
                self.dev.framerate = framerate


class CameraIR(Camera):
    ATTEMPS = 10

    def __init__(self):
        self.config = CameraConfig()
        Camera.__init__(
            self, "IR", self.config.IR.resolution.x, self.config.IR.resolution.y
        )
        self.BUF_SIZE = 10
        self.q = Queue(self.BUF_SIZE)
        self.PTR_PY_FRAME_CALLBACK = CFUNCTYPE(None, POINTER(uvc_frame), c_void_p)(
            self.__py_frame_callback
        )
        self.ctx = POINTER(uvc_context)()
        self.dev = POINTER(uvc_device)()
        self.devh = POINTER(uvc_device_handle)()
        self.ctrl = uvc_stream_ctrl()
        self.is_open = False
        self.frame_reader = None

    def open(self):
        attemp = 0
        if self.is_open:
            self.logger.warning("IR cam already open.")
            return 0
        while not self.is_open and attemp <= self.ATTEMPS:
            self.is_open = self.__init_thermal_data_frames()
            if not self.is_open:
                time.sleep(0.1)
                attemp = attemp + 1
            else:
                self.logger.info("IR camera opened succesfully.")
                return 0
            self.logger.error("Error while opening IR camera.")
            return -1

    def configure(self):
        frame_formats = uvc_get_frame_formats_by_guid(self.devh, VS_FMT_GUID_Y16)
        # Get the supported formats
        if len(frame_formats) == 0:
            self.logger.error("device does not support Y16")
            libuvc.uvc_unref_device(self.dev)
            return False
        libuvc.uvc_get_stream_ctrl_format_size(
            self.devh,
            byref(self.ctrl),
            UVC_FRAME_FORMAT_Y16,
            frame_formats[0].wWidth,
            frame_formats[0].wHeight,
            int(1e7 / frame_formats[0].dwDefaultFrameInterval),
        )

    def close(self):
        if self.is_open:
            self.is_open = False
            libuvc.uvc_close(self.devh)

    def start_capture(self):
        res = libuvc.uvc_start_streaming(
            self.devh, byref(self.ctrl), self.PTR_PY_FRAME_CALLBACK
        )
        if res < 0:
            self.logger.error("uvc_start_streaming failed: {0}".format(res))
            return False
        else:
            return True

    def stop_capture(self):
        libuvc.uvc_stop_streaming(self.devh)
        while not self.q.empty():
            self.q.get()

    def get_frame(self):
        try:
            data = self.q.get(True, 5)
            return np.copy(data)
        except Exception as e:
            self.logger.error("Timeout")
            self.logger.error(e)
            return None

    def __py_frame_callback(self, frame, userptr):
        array_pointer = cast(
            frame.contents.data,
            POINTER(c_uint16 * (frame.contents.width * frame.contents.height)),
        )
        data = np.frombuffer(array_pointer.contents, dtype=np.dtype(np.uint16)).reshape(
            frame.contents.height, frame.contents.width
        )
        assert frame.contents.data_bytes == (
            2 * frame.contents.width * frame.contents.height
        )

        if not self.q.full():
            self.q.put(data)

    def __init_thermal_data_frames(self):
        # Initialize libuvc library
        res = libuvc.uvc_init(byref(self.ctx), 0)
        if res < 0:
            self.logger.error(f"uvc_init error ({res})")
            return False
        # Find the Pure Thermal 2 device
        res = libuvc.uvc_find_device(
            self.ctx, byref(self.dev), PT_USB_VID, PT_USB_PID, 0
        )
        if res < 0:
            self.logger.error(f"uvc_find_device error ({res})")
            libuvc.uvc_exit(self.ctx)
            return False
        # Open the found device
        res = libuvc.uvc_open(self.dev, byref(self.devh))
        if res < 0:
            self.logger.error(f"uvc_open error ({res})")
            libuvc.uvc_unref_device(self.dev)
            return False
        return True

    def raw_to_8bit(self, data):
        odata = np.copy(data)
        cv.normalize(data, odata, 0, 65535, cv.NORM_MINMAX)
        np.right_shift(odata, 8, odata)
        odata = cv.applyColorMap(np.uint8(odata), cv.COLORMAP_INFERNO)
        return odata

    def performffc(self):
        perform_manual_ffc(self.devh)

    def print_shutter_info(self):
        print_shutter_info(self.devh)

    def setmanualffc(self):
        set_manual_ffc(self.devh)

    def setautoffc(self):
        set_auto_ffc(self.devh)
