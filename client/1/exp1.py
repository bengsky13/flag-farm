#!/usr/bin/env python3


import os, base64
import random


x = random.randint(1,2)
if x == 1:
    print("RTRTNI25{%s}" % base64.b64encode(os.urandom(16)).decode(), flush=True) 
else:
    print()