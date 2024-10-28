#!/bin/bash
set -e

# Set the paths to the app
CURRENT_PATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
VENV_PATH="$CURRENT_PATH/.venv"

# Activate python environment
source "$VENV_PATH/bin/activate"

# Export some configuration paths
export VISIONBIO_CONFIG_PATH="$CURRENT_PATH/config.yaml"
export PYTHONPATH="$CURRENT_PATH/View:$CURRENT_PATH/Model:$CURRENT_PATH/Controller:$CURRENT_PATH/Miscellaneous"

# Run the application
python -u $CURRENT_PATH/main.py
