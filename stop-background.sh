#!/bin/bash
kill -n SIGTERM $(pgrep -f "python3 -u tor_based.py")