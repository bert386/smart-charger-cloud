import os
import sys
import time
import datetime

import csv
import xml.etree.ElementTree
import random, string

conf_file_name = "config.xml"

### function to generate random string for Mqtt clientid
def randomword(length):
   return ''.join(random.choice(string.ascii_uppercase + string.digits) for i in range(length))

millis = lambda: int(round(time.time() * 1000))