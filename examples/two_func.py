
from pyvoom import jit

# Every function called by a target function must be also be annotated with '@jit'
# In other words, there is no support for calling back into Python from
# the jitted functions.

@jit
def func2(x):
    return 3*x

@jit
def func1(a,b):
    return b+func2(a) 

# On the first call to func1, func2 will be undefined.  The call is made in python,
# and the call the func2 will cause it to be translated.
print func1(2.0, 3.0)
# On the second call to func1, func2 is available.  This call to func1 is make is jitted.
print func1(3.0, 4.0)

# An alternate technique to warming up the JIT is to call the leaf functions first
print func2(1.0)
# Then call the top-most function, and all the leaf functions will be available.
print func1(5.0, 6.0)

