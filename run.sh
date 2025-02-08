#!/bin/bash
source ./test/bin/activate
export MESA_GL_VERSION_OVERRIDE=4.5
python3 main.py
