import ctypes 
Num = 16

fun = ctypes.CDLL('libfun.so')
fun.myFunction.argtypes = [ctypes.c_int]
