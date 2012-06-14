
from pyvoom import jit
from math import exp

@jit
def do_sum(a):
    s = 1.0
    for i in range(10000):
        x = 0.001*i
        s += exp(-a*x*x)
    return s

print do_sum(0.9) 




