
from pyvoom import jit
from math import exp
import numpy as np

@jit
def do_sum2(a):
    s = 1.0
    for j in range(200):
        y = 2.0 + .001*j
        for i in range(100):
            x = 1.0 + 0.002*i
            s += exp(-x*x-y*y)
    return s


print do_sum2(0.9) 
