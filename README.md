pyvoom
======

Another Python to LLVM converter

Prerequisites
-------------
 Requires LLVM and llvm-py.

Installation
------------
 There is no installer.  Set PYTHONPATH to the src/ directory.

Usage
-----
1. Import pyvoom, as 'from pyvoom import jit'
2. Put an '@jit' decorator before any function to be translated and executed using the LLVM JIT.

Example
-------

Simple function call.

    from pyvoom import jit

    @jit
    def func(a):
        return a + 2

    print func(2.0)


See the example/ directory for more examples.

What works
----------
* Expressions with +-*/,sqrt,exp on floats and integers
* Simple loops ('for i in range(100)' is the only form supported)
* Simple indexing into 1D Numpy arrays
