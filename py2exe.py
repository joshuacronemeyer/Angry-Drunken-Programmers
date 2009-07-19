# setup.py
from distutils.core import setup
import py2exe, glob
      
setup(windows=[{
   "script":"angrydd.py",
   "icon_resources": [(1, "angrydd.ico")]}
 ]

)