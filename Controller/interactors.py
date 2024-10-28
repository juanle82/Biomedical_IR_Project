"""Interactors."""
from functools import partial


class MainViewInteractor:
    def Install(self, presenter, view):
        self.presenter = presenter
        self.view = view
        self.view.canvas_ir.bind("<Button-1>", self.__onFrameClick)
        self.view.canvas_vis.bind("<Button-1>", self.__onFrameClick)
        self.view.saveOrClose_btn.configure(command=self.__onCapture)
        self.view.disable_btn.configure(command=self.__disableBtnCommand)
        self.view.process_btn.configure(command=self.__onShowProcessing)
        self.__configurePluginsBtn()

    #
    # Delegates
    #
    def __disableBtnCommand(self):
        self.presenter.onDisableSensors()
        self.view.onDisableSensors()

    def __onCapture(self):
        self.presenter.onSaveImagesOrClose()
        self.view.onCapture()

    def __onShowProcessing(self):
        self.view.onProcessing()

    def __onPlugin(self, key: str):
        self.presenter.onPlugin(key)

    def __onFrameClick(self, event):
        self.view.onFrameClick()

    #
    # Private
    #
    def __configurePluginsBtn(self):
        for key, btn in self.view.plugin_list.items():
            action = partial(self.__onPlugin, key)
            btn.configure(command=action)
