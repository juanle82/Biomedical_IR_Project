"""Views."""
import enum
import threading
import numpy as np
import tkinter as tk
import tkinter.font as font
import tkinter.ttk as ttk
from PIL import ImageTk, Image
import cv2 as cv
from Miscellaneous.config import ViewConfig
from Plugins import *


class MainView(tk.Tk):
    class ViewMode(enum.Enum):
        CAPTURE = 1
        CLOSE = 2

    ###########################################################################
    # Initialization methods
    ###########################################################################
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.config = ViewConfig()
        w, h = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("%dx%d+0+0" % (w, h))
        self.attributes("-fullscreen", True)
        self.mainFrame = tk.Frame(self, height=h, width=w)
        self.mainFrame.pack(expand=True)
        # Create view layout
        self.__createLayout(self.config)
        # Create object to implement logic in view
        self.__initLogic()

    def __createLayout(self, config):
        # Create canvas for images
        self.__createCanvas()
        # Create buttons
        self.__createButtons(config)
        # Create plugin button list
        self.plugin_list = {}

    def __createCanvas(self):
        # Create canvas layout for images
        w, h = self.winfo_screenwidth(), self.winfo_screenheight()
        self.width = w
        self.height = h
        self.canvas_ir = CanvasImg(
            self.mainFrame, width=w // 2, height=h, highlightthickness=0, relief="ridge"
        )
        self.canvas_vis = CanvasImg(
            self.mainFrame, width=w // 2, height=h, highlightthickness=0, relief="ridge"
        )
        self.canvas_ir.grid(row=0, column=0)
        self.canvas_vis.grid(row=0, column=1)
        self.canvas_ir.img = Image.new("RGB", (w // 2, h))
        self.canvas_vis.img = Image.new("RGB", (w // 2, h))
        self.canvas_ir.photo = ImageTk.PhotoImage(self.canvas_ir.img)
        self.canvas_vis.photo = ImageTk.PhotoImage(self.canvas_vis.img)
        tmp = self.canvas_ir.create_image(
            0, 0, image=self.canvas_ir.photo, anchor=tk.NW
        )
        self.canvas_ir.item = tmp
        tmp = self.canvas_vis.create_image(
            0, 0, image=self.canvas_vis.photo, anchor=tk.NW
        )
        self.canvas_vis.item = tmp

    def __createButtons(self, config):
        w, h = self.winfo_screenwidth(), self.winfo_screenheight()
        self.update()
        self.visFrame = tk.Frame(self.mainFrame, height=h, width=w // 2)
        self.visFrame.grid(row=0, column=1)
        # Create button widgets
        b = tk.Button(
            self.visFrame,
            text="Capture",
            anchor=tk.CENTER,
            font=font.Font(size=config.buttons.FontSize),
            width=config.buttons.Size.w,
            height=config.buttons.Size.h,
        )
        b["state"] = "disabled"
        self.saveOrClose_btn = b
        b = tk.Button(
            self.visFrame,
            text="Disable\nsensors",
            anchor=tk.CENTER,
            font=font.Font(size=config.buttons.FontSize),
            width=config.buttons.Size.w,
            height=config.buttons.Size.h,
        )
        self.disable_btn = b
        b = tk.Button(
            self.visFrame,
            text="Process\nroutines",
            anchor=tk.CENTER,
            font=font.Font(size=config.buttons.FontSize),
            width=config.buttons.Size.w,
            height=config.buttons.Size.h,
        )
        b["state"] = "disabled"
        self.process_btn = b
        # Place buttons in grid
        self.process_btn.grid(row=0, column=0)
        self.saveOrClose_btn.grid(row=1, column=0)
        self.disable_btn.grid(row=2, column=0)
        # Place the frame in canvas
        x = self.canvas_vis.winfo_width() - config.buttons.Padding.x
        y = self.canvas_vis.winfo_height() - config.buttons.Padding.y
        window = self.canvas_vis.create_window(x, y, anchor=tk.SE, window=self.visFrame)
        self.saveOrClose_btn_window = window
        self.update()

    def __initLogic(self):
        self.mode = self.ViewMode.CAPTURE
        self.on_capture_vis = False
        self.on_capture_ir = False

    ###########################################################################
    # Class properties
    ###########################################################################
    @property
    def img_ir(self):
        return self._img_ir

    @img_ir.setter
    def img_ir(self, value):
        self._img_ir = np.copy(value)
        canvas = self.canvas_ir
        new_img = self.__adjustToCanvas(value, canvas, "IR")
        self.after(0, self.__updateIrImg(new_img, canvas))

    @property
    def img_vis(self):
        return self._img_vis

    @img_vis.setter
    def img_vis(self, value):
        self._img_vis = np.copy(value)
        canvas = self.canvas_vis
        new_img = self.__adjustToCanvas(value, canvas, "VIS")
        self.after(0, self.__updateVisImg(new_img, canvas))

    ###########################################################################
    # Public methods
    ###########################################################################
    def onDisableSensors(self):
        if self.mode == self.ViewMode.CLOSE:
            self.captureEnable(True)
            self.saveOrClose_btn["text"] = "Close"
            self.disable_btn["text"] = "Enable\nsensors"
            self.process_btn.grid_forget()
            self.__processingMenuEnable(False)
        else:
            self.saveOrClose_btn["text"] = "Capture"
            self.disable_btn["text"] = "Disable\nsensors"
            self.process_btn["state"] = "normal"

    def captureEnable(self, is_enable):
        if is_enable:
            self.saveOrClose_btn["state"] = "normal"
            self.process_btn["state"] = "normal"
            self.process_btn.grid(row=0, column=0)
        else:
            self.saveOrClose_btn["state"] = "disabled"

    def switchMode(self):
        if self.mode == self.ViewMode.CAPTURE:
            self.mode = self.ViewMode.CLOSE
        else:
            self.mode = self.ViewMode.CAPTURE

    def getMode(self):
        return self.mode

    def onCapture(self):
        if self.getMode() == self.ViewMode.CAPTURE:
            self.on_capture_vis = True
            self.on_capture_ir = True

    def onProcessing(self):
        if self.process_frame.winfo_ismapped():
            self.__processingMenuEnable(False)
        else:
            self.__processingMenuEnable(True)

    def onFrameClick(self):
        if self.process_frame.winfo_ismapped():
            self.__processingMenuEnable(False)

    def close(self):
        self.destroy()

    def configurePlugins(self, plugins=None):
        pw = tk.Frame(
            self,
            width=int(self.config.processMenu.Width),
            height=self.winfo_screenheight(),
            bg="#26242f",
        )
        self.process_frame = pw

        config = self.config
        pw.pack_propagate(False)
        b_font = font.Font(size=config.processMenu.FontSize)

        btn = tk.Button(
            pw,
            bd=0,
            highlightthickness=0,
            fg="white",
            bg="#26242f",
            text="None",
            font=b_font,
        )
        btn.pack(anchor="w", fill="x", ipady=20)
        self.plugin_list["None"] = btn

        if plugins is not None:
            for plugin in plugins:
                p = plugin()
                pname = p.name
                btn = tk.Button(
                    pw,
                    bd=0,
                    highlightthickness=0,
                    fg="white",
                    bg="#26242f",
                    text=pname,
                    font=b_font,
                )
                btn.pack(anchor="w", fill="x", ipady=20)
                self.plugin_list[pname] = btn

    ###########################################################################
    # Private methods
    ###########################################################################
    def __updateIrImg(self, new_img, canvas):
        self.canvas_ir = self.__updateCanvasImg(new_img, canvas)

    def __updateVisImg(self, new_img, canvas):
        self.canvas_vis = self.__updateCanvasImg(new_img, canvas)

    def __updateCanvasImg(self, new_img, canvas):
        # IMPORTANT: The command order must be preserved to avoid flickering
        # in the image
        canvas.img = Image.fromarray(new_img)
        tmp = ImageTk.PhotoImage(canvas.img)
        canvas.itemconfig(canvas.item, image=tmp)
        canvas.photo = tmp
        return canvas

    def __adjustToCanvas(self, new_img, canvas, type):
        canvas_img = self.__resizeAndCrop(new_img, (self.height, self.width // 2), type)
        # To make the capture effect
        if type == "VIS" and self.on_capture_vis:
            canvas_img = cv.cvtColor(canvas_img, cv.COLOR_RGB2RGBA)
            canvas_img[:, :, 3] = canvas_img[:, :, 3] * 0.5
            self.on_capture_vis = False
        elif type == "IR" and self.on_capture_ir:
            canvas_img = cv.cvtColor(canvas_img, cv.COLOR_RGB2RGBA)
            canvas_img[:, :, 3] = canvas_img[:, :, 3] * 0.5
            self.on_capture_ir = False

        return canvas_img

    def __resizeAndCrop(self, img, size, type):
        h, w = img.shape[:2]
        sh, sw = size
        # interpolation method
        if h > sh or w > sw:  # shrinking image
            interp = cv.INTER_AREA
        else:  # stretching image
            interp = cv.INTER_CUBIC
        # check the higher dimension
        if sh > sw:
            scale = sh / h
        else:
            scale = sw / w
        # new image sizes
        new_w = int(scale * w)
        new_h = int(scale * h)
        # scale
        scaled_img = cv.resize(img, (new_w, new_h), interpolation=interp)
        # crop the image respect the center
        dw = 0
        if new_w > sw:
            dw = new_w // 2 - sw // 2
        dh = 0
        if new_h > sh:
            dh = new_h // 2 - sh // 2
        scaled_img = scaled_img[int(dh) : int(new_h - dh), int(dw) : int(new_w - dw)]
        # convert to RGB image
        if type == "IR":
            scaled_img = cv.cvtColor(scaled_img, cv.COLOR_BGR2RGB)
        return scaled_img

    def __processingMenuEnable(self, is_enable):
        if not is_enable:
            self.process_frame.place_forget()
        else:
            self.process_frame.place(x=0, y=0)


class CanvasImg(tk.Canvas):
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
        self.img = None
        self.photo = None
        self.item = None
