#!/usr/bin/env python3


import os, base64
import random
import sys

ip = sys.argv[1]
x = random.randint(1,2)
print("Hello attacking", ip)
if x == 1:
    print("FLAG{%s}" % base64.b64encode(os.urandom(16)).decode(), flush=True) 
else:
    print()