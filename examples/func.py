
from pyvoom import jit

@jit
def jit_func(a):
    return a + 2

def python_func(a):
    return a + 2

# Two different translations of the function get created based on 
# on the different types of the function parameters
print jit_func(1.0)
print jit_func(2)

print 'value from Python : ',python_func(2.5)
print 'value from jitted function : ',jit_func(2.5)

