# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import logging
import os
import json


def readfile(dir_path, filename):
    cwd = os.path.abspath(os.curdir)
    path = "%s/%s/%s" % (cwd, dir_path, filename)
    with open(path, "r") as fp:
        return json.load(fp)


def log_unittest(unittest_obj, msg, log_level="info"):
    log = "%s %s" % (log_level.upper(), unittest_obj.id())
    if unittest_obj.shortDescription():
        log += " -- %s" % unittest_obj.shortDescription()
    log += " - %s" % msg
    getattr(logging, log_level)(log)
