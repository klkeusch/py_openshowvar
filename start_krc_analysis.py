import os
import sys

os.system("start /B start cmd.exe @cmd /k ping 8.8.8.8 -t ")
os.system("start /B start cmd.exe @cmd /k python py_openshowvar.py")
