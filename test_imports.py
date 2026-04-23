#!/usr/bin/env python
import sys
print("Python script started")
print(f"Python version: {sys.version}")
print(f"Python path: {sys.executable}")

try:
    import django
    print("Django imported successfully")
except ImportError as e:
    print(f"Django import error: {e}")

try:
    import lightgbm
    print("LightGBM imported successfully")
except ImportError as e:
    print(f"LightGBM import error: {e}")

try:
    import sklearn
    print("Sklearn imported successfully")
except ImportError as e:
    print(f"Sklearn import error: {e}")

print("Test complete")
