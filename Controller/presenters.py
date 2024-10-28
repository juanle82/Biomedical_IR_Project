from datetime import datetime
import logging
import logging.handlers
from datetime import datetime
import threading
import time
import os
import cv2 as cv
import numpy as np
from Miscellaneous import cameras
from Plugins import *


class MainViewPresenter:
    ###########################################################################
    # Initialization methods
    ###########################################################################
    def __init__(self, model, view, interactor):
        self.model = model
        self.view = view
        self.__init_logic()
        self.__init_plugins()
        self.__init_cameras()
        self.__init_view()
        interactor.Install(self, view)
        self.__start_threads()

    def __init_view(self):
        self.__load_view_from_model()
        self.view.configurePlugins(PluginBase.__subclasses__())
        # Enable capture button
        self.view.captureEnable(True)

    def __init_logic(self):
        # Logger
        self.logger = logging.getLogger(__name__)
        # Create a log file for debugging
        if getattr(sys, "frozen", False):
            path = os.path.dirname(sys.executable)
        else:
            path = os.getcwd()
        path = os.path.join(path, "log")
        if not os.path.exists(path):
            os.makedirs(path)
        path = os.path.join(path, f"debug.log")
        debuglogger_fh = logging.handlers.RotatingFileHandler(
            path, maxBytes=10240, backupCount=5
        )
        debuglogger_fh.setLevel(logging.DEBUG)
        fmt = "%(asctime)s\t%(name)s:%(lineno)d\t%(levelname)s\t%(message)s"
        formatter = logging.Formatter(fmt)
        debuglogger_fh.setFormatter(formatter)
        for _, item in logging.root.manager.loggerDict.items():
            if isinstance(item, logging.Logger):
                item.setLevel(logging.INFO)
                item.addHandler(debuglogger_fh)
        self.logger.setLevel(logging.DEBUG)
        # Flags
        self.camIsEnable = False
        self.IRcamIsRunning = False
        self.VIScamIsRunning = False
        self.disableFlag = False
        # Mutexes
        self._saveLock = threading.Lock()
        self._getImg = threading.Lock()
        # Process threads
        self.cam_IR_Thread = threading.Thread(target=self.__cam_IR_loop)
        self.cam_VIS_Thread = threading.Thread(target=self.__cam_VIS_loop)
        self.auxThread = threading.Thread(target=self.__saveImages)
        # Semaphores
        self.cam_IR_sem = threading.Semaphore(0)
        self.cam_VIS_sem = threading.Semaphore(0)

    def __init_cameras(self):
        self.IRcam = cameras.CameraIR()
        self.VIScam = cameras.CameraVIS()
        self.__VIScam_open_and_config()

    def __init_plugins(self):
        self.plugin_list = {}
        for plugin in PluginBase.__subclasses__():
            p = plugin()
            self.plugin_list[p.name] = p
        self.currentPlugin = None

    ###########################################################################
    # Public methods
    ###########################################################################

    def start(self):
        self.view.mainloop()

    def onSaveImagesOrClose(self):
        # Check the view mode
        mode = self.view.getMode()
        # Get the devices status
        if mode == self.view.ViewMode.CAPTURE:
            self.onSaveImages()
        elif mode == self.view.ViewMode.CLOSE:
            self.onClose()

    def onSaveImages(self):
        self.logger.debug("On Save.")
        if not self.auxThread.is_alive():
            self.auxThread = threading.Thread(target=self.__saveImages)
            self.auxThread.start()

    def onClose(self):
        self.logger.debug("On close")
        self.__stop_threads(True)
        self.__VIScam_close()
        self.view.close()

    def onDisableSensors(self):
        # Check the current mode
        mode = self.view.getMode()
        # Disable this button to avoid race conditions
        if (
            mode == self.view.ViewMode.CAPTURE
            and not self.IRcamIsRunning
            or not self.VIScamIsRunning
            and self.disableFlag
        ):
            self.logger.debug("The disable button busy.")
            return
        elif (
            mode == self.view.ViewMode.CLOSE
            and self.IRcamIsRunning
            or self.VIScamIsRunning
            and self.disableFlag
        ):
            self.logger.debug("The disable button busy.")
            return
        else:
            self.disableFlag = True
        if mode == self.view.ViewMode.CAPTURE:
            if not (self.VIScamIsRunning or self.IRcamIsRunning):
                self.logger.warn("Returning the cameras aren't running yet.")
                self.disableFlag = False
                return
        elif mode == self.view.ViewMode.CLOSE:
            if self.VIScamIsRunning or self.IRcamIsRunning:
                self.logger.warn("Returning the cameras are running yet.")
                self.disableFlag = False
                return
        # Check if temporary thread is alive and if it exists wait
        if hasattr(self, "tmpThread"):
            if self.tmpThread.is_alive():
                self.tmpThread.join(5)
        # Reset the plugins if someone selected
        self.currentPlugin = None
        # Check the view mode
        if mode == self.view.ViewMode.CLOSE:
            self.logger.info("Restarting threads...")
            self.tmpThread = threading.Thread(target=self.__restart_threads)
            self.tmpThread.start()
        elif mode == self.view.ViewMode.CAPTURE:
            self.logger.info("Stopping threads...")
            self.tmpThread = threading.Thread(target=self.__stop_threads)
            self.tmpThread.start()
        # Switch the mode
        self.view.switchMode()
        # Enable capture button
        self.view.captureEnable(True)

    def onPlugin(self, plugin_name: str):
        if plugin_name == "None":
            self.currentPlugin = None
        else:
            self.currentPlugin = self.plugin_list[plugin_name]

    ###########################################################################
    # Private methods
    ###########################################################################

    def __load_view_from_model(self):
        with self._getImg:
            self.view.img_vis = self.model.img_vis
            self.view.img_ir = self.model.img_ir

    def __start_threads(self):
        self.camIsEnable = True
        self.cam_IR_Thread.start()
        self.cam_VIS_Thread.start()
        self.disableFlag = False

    def __restart_threads(self):
        self.cam_IR_Thread = threading.Thread(target=self.__cam_IR_loop)
        self.cam_VIS_Thread = threading.Thread(target=self.__cam_VIS_loop)
        self.__start_threads()

    def __stop_threads(self, is_closing=False):
        self.camIsEnable = False
        if is_closing:
            self.cam_VIS_sem.release()
            self.cam_IR_sem.release()
        # Wait until camera threads end
        if self.cam_IR_Thread.is_alive():
            self.logger.info("Waiting IR thread...")
            self.cam_IR_Thread.join(5)
        if self.cam_VIS_Thread.is_alive():
            self.logger.info("Waiting VIS thread...")
            self.cam_VIS_Thread.join(5)
        # Wait until save thread exits if alive
        if self.auxThread.is_alive():
            self.logger.info("Waiting auxiliar thread...")
            self.auxThread.join(5)
        self.disableFlag = False
        # Reset images
        with self._getImg:
            self.model.img_vis = np.zeros((1024, 1024, 3), np.uint8)
            self.model.img_ir = np.zeros((1024, 1024, 3), np.uint8)
        self.__load_view_from_model()

    def __cam_IR_loop(self):
        self.logger.info("On IR camera loop")
        isFirstTime = True
        ret = -1
        # Open the device
        while (ret < 0) and self.camIsEnable:
            ret = self.IRcam.open()
        # Configure the device
        # self.IRcam.configure(fps=30)
        self.IRcam.configure()
        # Start video streaming
        self.IRcam.start_capture()
        # Getting the data as soon as they are available
        while self.camIsEnable:
            thermal_data = self.IRcam.get_frame()
            # To synchronise the first capture
            if isFirstTime and thermal_data is not None and self.camIsEnable:
                self.IRcamIsRunning = True
                self.cam_VIS_sem.release()
                if not self.cam_IR_sem.acquire(timeout=10):
                    self.logger.error("The VIS cam has failed.")
                    self.view.after(0, self.onClose)
                    break
                if not self.VIScamIsRunning:
                    self.logger.warn("The VIS cam isn't running.")
                    break
                isFirstTime = False
            if thermal_data is not None and self.camIsEnable:
                with self._getImg:
                    self.model.img_ir_raw = thermal_data
                    self.model.img_ir = self.IRcam.raw_to_8bit(thermal_data)
                    if self.currentPlugin is not None:
                        try:
                            thermal_proc = self.currentPlugin.ProcessImage(thermal_data)
                            # Convert the processed image if it's in incompatible format
                            if thermal_proc.dtype != "uint8":
                                thermal_proc = self.IRcam.raw_to_8bit(thermal_proc)
                        except Exception as e:
                            self.logger.error(e)
                            thermal_proc = self.model.img_ir
                    else:
                        thermal_proc = self.model.img_ir
                    self.model.img_ir_processed = thermal_proc
                    self.view.img_ir = self.model.img_ir_processed
        self.logger.info("IR camera loop ends.")
        self.IRcam.stop_capture()
        self.IRcam.close()
        self.IRcamIsRunning = False

    def __cam_VIS_loop(self):
        self.logger.info("On VISIBLE camera loop")
        isFirstTime = True
        # Capture frames
        while self.camIsEnable:
            ret, tmp = self.VIScam.capture()
            # To synchronise the first capture
            if isFirstTime and self.camIsEnable and tmp is not None:
                self.VIScamIsRunning = True
                self.cam_IR_sem.release()
                if not self.cam_VIS_sem.acquire(timeout=10):
                    self.logger.error("The IR cam has failed.")
                    self.view.after(0, self.onClose)
                    break
                if not self.IRcamIsRunning:
                    self.logger.warn("The IR cam isn't running.")
                    break
                isFirstTime = False
            if ret and self.camIsEnable and tmp is not None:
                with self._getImg:
                    if tmp is not None:
                        self.model.img_vis = tmp
                        self.view.img_vis = self.model.img_vis
        self.logger.info("VIS camera loop ends.")
        self.VIScamIsRunning = False

    def __saveImages(self):
        if self.currentPlugin is not None:
            saveProc = True
        else:
            saveProc = False
        rootPath = self.model.config.saveFolder
        img_ir_proc = np.zeros((1, 1, 3), np.uint8)
        with self._saveLock:
            if not os.path.exists(rootPath):
                os.makedirs(rootPath)
            timestamp = datetime.now().strftime("%d_%m_%Y__%H_%M_%S")
            rootPath = os.path.join(rootPath, timestamp)
            with self._getImg:
                _, img_vis = self.VIScam.take_photo()
                img_ir = self.model.img_ir
                if self.currentPlugin is not None:
                    img_ir_proc = self.model.img_ir_processed
                img_ir_raw = self.model.img_ir_raw
            img_vis = cv.cvtColor(img_vis, cv.COLOR_RGB2BGR)
            self.logger.info("Saving visible...")
            cv.imwrite(rootPath + "_visible" + ".png", img_vis)
            self.logger.info("Saving IR...")
            cv.imwrite(rootPath + "_ir" + ".png", img_ir)
            if saveProc:
                self.logger.info("Saving processed IR...")
                cv.imwrite(rootPath + "_ir_proc" + ".png", img_ir_proc)
            # Save RAW data of IR image
            # Add two words at the begging with minimum and maximum values
            self.logger.info("Saving raw IR...")
            IRfilename = rootPath + "_ir" + ".bin"
            fp = open(IRfilename, "ab")
            firstWords = np.array([img_ir_raw.min(), img_ir_raw.max()], dtype=np.uint16)
            firstWords.astype("uint16").tofile(fp)
            img_ir_raw.astype("uint16").tofile(fp)
            fp.close()

    def __VIScam_open_and_config(self):
        ret = -1
        # Open the device
        while ret < 0:
            ret = self.VIScam.open()
            if ret < 0:
                self.logger.error("The VIS cam cannot be opened. Trying again...")
        # Configure the device
        self.VIScam.configure()

    def __VIScam_close(self):
        self.VIScam.close()
