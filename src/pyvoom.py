
# experiments with Python ast

import ast
from llvm import *
from llvm.core import *
from llvm.ee import *
from llvm.passes import *
from converter import convert,my_module,func_ret_types,ty_float,ty_int,_numpy_struct
from dump_ast import dump

import numpy


ee = ExecutionEngine.new(my_module)

g_llvm_pass_manager = FunctionPassManager.new(my_module)
g_llvm_pass_manager.add(ee.target_data)
g_llvm_pass_manager.add(PASS_INSTRUCTION_COMBINING)
g_llvm_pass_manager.add(PASS_REASSOCIATE)
g_llvm_pass_manager.add(PASS_GVN)
g_llvm_pass_manager.initialize()


def count_rspaces(st):
    count = 0 
    for s in st:
        if s == ' ':
            count += 1
        else:
            break
    return count

def find_end(lines):
    initial_indent = count_rspaces(lines[0])
    idx = 1
    for l in lines[1:]:
        indent = count_rspaces(l)
        if indent == initial_indent:
            return idx
        idx += 1
    return idx

debug_output = False

jit_cache = {}
def jit(target_f):
    name = target_f.func_name
    def do_llvm_compile(args):
        if debug_output:
            print '****'
            print 'doing llvm compile'
            print '****'
        fname = target_f.func_code.co_filename
        ff = open(fname,'r')
        lines = [l for l in ff.readlines()]
        ff.close()
        lineno = target_f.func_code.co_firstlineno
        endlineno = lineno + find_end(lines[lineno:])
        an = ast.parse(''.join(lines[lineno:endlineno]))
         
        cvt = convert(args=args, env=target_f.__globals__)
        cvt.determine_types(an)
        if cvt._unknown_function_present:
            return None, None
        if debug_output:
            dump(an)
        e = cvt(an)
        if debug_output:
            print 'e = ',e
        e.verify()
        g_llvm_pass_manager.run(e)
        if debug_output:
            print 'after opt = ',e
        func_ret_types[name] = cvt._return_type
        return e,cvt._return_type
    def do_compile(*args):
        signature = name + str([type(a) for a in args])
        compiled_f = None
        if signature in jit_cache:
            compiled_f, ret_type = jit_cache[signature]
        else:
            if debug_output:
                print 'Function not already compiled: ',name
            compiled_f, ret_type = do_llvm_compile(args)
            if compiled_f:
                jit_cache[signature] = compiled_f, ret_type
        if not compiled_f:
            if debug_output:
                print 'executing in CPython ',name
            return target_f(*args)
        ee_args = []
        for a in args:
            if isinstance(a, int):
                ee_args.append(GenericValue.int(ty_int, a))
            elif isinstance(a, float):
                ee_args.append(GenericValue.real(ty_float, a))
            elif isinstance(a, numpy.ndarray):
                ee_args.append(GenericValue.pointer(Type.pointer(_numpy_struct),id(a)))
            else:
                print 'arg type not handled',a,type(a)

        ret = ee.run_function(compiled_f, ee_args)
        if ret_type == int:
            return ret.as_int()
        elif ret_type == float:
            return ret.as_real(ty_float)
        print 'return type unknown = ',ret_type

    return do_compile

