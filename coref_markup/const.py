import platform


NOT_MAC = (platform.system() != "Darwin")
LEFT_MOUSECLICK = 1
RIGHT_MOUSECLICK = 3 if NOT_MAC else 2
