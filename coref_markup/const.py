import platform


MAC = (platform.system() == "Darwin")
LEFT_MOUSECLICK = 1
RIGHT_MOUSECLICK = 3 if not MAC else 2
