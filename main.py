"""Biomedical example."""
import logging
from Controller import presenters
from Controller import interactors
from View import views
from Model import models


if __name__ == "__main__":
    logging.info("BIOMEDICAL VISIBLE AND IR APPLICATION")
    presenter = presenters.MainViewPresenter(
        models.MainViewModel(), views.MainView(), interactors.MainViewInteractor()
    )

    presenter.start()
