
from pyvoom import jit
import numpy as np


@jit
def do_index(c):
    a = c[1] 
    return a + 2
    
b = np.array([1.0,2.0,3.0])
print do_index(b)



