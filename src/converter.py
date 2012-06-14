
# experiments with Python ast

import ast
from pattern_match import *
from llvm import *
from llvm.core import *
from llvm.passes import *

import numpy



# Copied from Numba
_pyobject_head = [Type.int(64), Type.pointer(Type.int(32))]
_head_len = len(_pyobject_head)
_intp = Type.int(64)
_intp_star = Type.pointer(_intp)
_void_star = Type.pointer(Type.int(8))
_numpy_struct = Type.struct(_pyobject_head+\
      [_void_star,          # data
       Type.int(32),     # nd
       _intp_star,          # dimensions
       _intp_star,          # strides
       _void_star,          # base
       _void_star,          # descr
       Type.int(32),     # flags
       _void_star,          # weakreflist 
       _void_star,          # maskna_dtype
       _void_star,          # maskna_data
       _intp_star,          # masna_strides
      ])
# end copy


my_module = Module.new('my_module')
ty_int = Type.int()
ty_float = Type.double()
bb = None
builder = None
f_func = None

# tables for functions - stores the return type and the function types
func_ret_types = {}
func_types = {}



class convert(object):
    def __init__(self, args=None, env=None):
        self._args = args
        self._syms = {}   # types of symbols
        self._sym_cache = {}  # results of assignments
        self._return_type = None
        self._unknown_function_present = False
        self._env = {}
        if env != None:
            self._env = env

    def is_subset(self, t1, t2):
        if isinstance(t1,tuple):
            return t2 in t1
        else:
            return t1 == t2

    def combine(self, t1, t2):
        if t1 == (int,float) and t2 == int:
            return int
        if t1 == int and t2 == (int, float):
            return int
        if t1 == (int,float) and t2 == float:
            return float
        if t1 == float and t2 == (int, float):
            return float
        if t1 == t2:
            return t1
        if t1 == float or t2 == float:
            return float
        print ' combine types not handled',t1,t2

    def determine_types(self, an):
        """ This pass determines
            - integer constants will be needed as floating point or integer. 
            - whether called functions have been translated already. """
        m = Match(an)
        v = AutoVar()
        if m(ast.BinOp, left=v.e1, right=v.e2):
            t1 = self.determine_types(v.e1)
            t2 = self.determine_types(v.e2)
            rt = self.combine(t1,t2)
            return rt

        if m(ast.UnaryOp, operand=v.e1):
            return self.determine_types(v.e1)

        if m(ast.Num, n=v.e1):
            if type(v.e1) == int:
                return int
            return type(v.e1)
        if m(ast.Name, id=v.e1):
            if v.e1 in self._syms:
                return self._syms[v.e1]
            #print 'Name not found in symbol table',v.e1
            return None
        if m(ast.Module):
            return self.determine_types([a for a in ast.iter_child_nodes(an)][0])

        if m(ast.Assign, targets=[P(ast.Name, id=v.t)], value=v.x) or \
           m(ast.AugAssign, target=P(ast.Name, id=v.t), value=v.x):
            #if len(v.t) != 1: 
            #    print 'Assignment to multiple values not handled'
            t = self.determine_types(v.x) 
            self.set_types(v.x, t)
            name = str(v.t)
            if name in self._syms:
                 value = self._syms[name]
                 if value != t:
                    print 'inconsistent type for ',name,value,t
            else:
                self._syms[name] = t
            return t

        if m(ast.FunctionDef, args=v.args, body=v.body):
            args = [arg.id for arg in v.args.args]
            self._func_args = args

            for arg,val in zip(args,self._args):
                self._syms[arg] = type(val)
            t = None
            for e in v.body:
                t = self.determine_types(e)
                self.set_types(e,t)
            return t

        #if m(ast.Call, func=P(ast.Name, id="sum"), args=v.args):
        #    for a in v.args:
        #        self.determine_types(a)
        #    # assume only summing numpy arrays for now
        #    an._target_type = float
        #    return float

        if m(ast.Call, func=P(ast.Name, id="exp"), args=v.args) or \
           m(ast.Call, func=P(ast.Attribute, value=P(ast.Name, id="math"), attr="exp"), args=v.args):
            if len(v.args) != 1:
                print 'wrong number of args to exp(), # args = ',len(v.args)
            self.set_types(v.args[0], float)
            return float

        if m(ast.Call, func=P(ast.Name, id="sqrt"), args=v.args) or \
           m(ast.Call, func=P(ast.Attribute, value=P(ast.Name, id="math"), attr="sqrt"), args=v.args):
            if len(v.args) != 1:
                print 'wrong number of args to sqrt(), # args = ',len(v.args)
            self.set_types(v.args[0], float)
            return float

        if m(ast.Call, func=v.name, args=v.args):
            for a in v.args:
                t = self.determine_types(a)
                self.set_types(a, t)
            # look up function in table - if found, return it's return type
            #   if not, set a flag or throw an exception?
            
            if v.name.id not in func_ret_types:
                self._unknown_function_present = True
            return func_ret_types.get(v.name.id)

        if m(ast.Subscript, value=v.value, slice=v.slice):
            # for now, assume all array are 1-d floats
            an._target_type = self._syms[v.value.id]
            return float
            #return int

        if m(ast.For, body=v.body):
            for b in v.body:
                self.determine_types(b)
            return None

            
        if m(ast.Return, value=v.e):
            t = self.determine_types(v.e)
            self.set_types(v.e, t)
            self._return_type = t
            return t

            

    def set_types(self, an, target_type):
        m = Match(an)
        v = AutoVar()
        if m(ast.Num):
            an.target_type = target_type
        if m(ast.Name):
            an.target_type = target_type
        if m(ast.BinOp, left=v.e1, right=v.e2):
            t1 = self.set_types(v.e1, target_type)
            t2 = self.set_types(v.e2, target_type)
            an.target_type = target_type
        if m(ast.UnaryOp, operand=v.e1):
            self.set_types(v.e1, target_type)
            an.target_type = target_type

    
    def __call__(self, an, **kw):
        m = Match(an)
        v = AutoVar()

        add_name = []
        if 'use_name' in kw:
            add_name = [kw['use_name']]

        if m(ast.Module):
            return self([a for a in ast.iter_child_nodes(an)][0])
    
        if m(ast.FunctionDef, name=v.name, args=v.args, body=v.body):
            global builder,f_func
            args = [arg.id for arg in v.args.args]
            new_args = []
            if self._args:
                for a in self._args:
                    if isinstance(a, int):
                        new_args.append(ty_int)
                    elif isinstance(a, float):
                        new_args.append(ty_float)
                    elif isinstance(a, numpy.ndarray):
                        new_args.append(Type.pointer(_numpy_struct))
                    else:
                        print 'arg type not handled',type(a)
            
            else:
                new_args = [ty_int]*len(args)

            for arg,val in zip(args,self._args):
                self._syms[arg] = type(val)
            tr = self._return_type
            if tr == int:
                ty_f = Type.function(ty_int, new_args)
            elif tr == float:
                ty_f = Type.function(ty_float, new_args)
            else:
                print 'return type not handled',tr
            f_func = my_module.add_function(ty_f, v.name)
            func_types[v.name] = ty_f
            bb = f_func.append_basic_block("entry")
            builder = Builder.new(bb)
            b = None
            for e in v.body:
                self(e)
            return f_func
        if m(ast.Assign, targets=[P(ast.Name, id=v.t)], value=v.x):
            val = self(v.x, use_name=v.t)
            loc = builder.alloca(ty_float, v.t)
            builder.store(val, loc)
            #self._sym_cache[str(v.t[0].id)] = val
            self._sym_cache[str(v.t)] = val,loc
            return val
        if m(ast.AugAssign, op=ast.Add, target=P(ast.Name, id=v.t), value=v.x):
            val, loc = self._sym_cache[str(v.t)]
            a1 = builder.load(loc)
            a2 = self(v.x)
            val = builder.fadd(a1, a2, *add_name)
            builder.store(val, loc)
            #self._sym_cache[str(v.t[0].id)] = val
            #self._sym_cache[str(v.t)] = val,loc
            return val
        if m(ast.BinOp, op=ast.Add, left=v.e1, right=v.e2, target_type=int):
            a1 = self(v.e1)
            a2 = self(v.e2)
            return builder.add(a1, a2, *add_name)
        if m(ast.BinOp, op=ast.Add, left=v.e1, right=v.e2, target_type=float):
            a1 = self(v.e1)
            a2 = self(v.e2)
            return builder.fadd(a1, a2, *add_name)
        if m(ast.BinOp, op=ast.Sub, left=v.e1, right=v.e2, target_type=int):
            a1 = self(v.e1)
            a2 = self(v.e2)
            return builder.sub(a1, a2, *add_name)
        if m(ast.BinOp, op=ast.Sub, left=v.e1, right=v.e2, target_type=float):
            a1 = self(v.e1)
            a2 = self(v.e2)
            return builder.fsub(a1, a2, *add_name)
        if m(ast.BinOp, op=ast.Mult, left=v.e1, right=v.e2, target_type=int):
            a1 = self(v.e1)
            a2 = self(v.e2)
            return builder.mul(a1, a2, *add_name)
        if m(ast.BinOp, op=ast.Mult, left=v.e1, right=v.e2, target_type=float):
            a1 = self(v.e1)
            a2 = self(v.e2)
            return builder.fmul(a1, a2, *add_name)
        if m(ast.BinOp, op=ast.Div, left=v.e1, right=v.e2, target_type=int):
            a1 = self(v.e1)
            a2 = self(v.e2)
            return builder.div(a1, a2, *add_name)
        if m(ast.BinOp, op=ast.Div, left=v.e1, right=v.e2, target_type=float):
            a1 = self(v.e1)
            a2 = self(v.e2)
            return builder.fdiv(a1, a2, *add_name)
        if m(ast.BinOp, op=ast.Pow, left=v.e1, right=P(ast.Num,n=2), target_type=float):
            a1 = self(v.e1)
            return builder.fmul(a1, a1, *add_name)
        if m(ast.UnaryOp, op=ast.USub, operand=v.e1, target_type=float):
            a1 = self(v.e1)
            return builder.fmul(Constant.real(ty_float,-1), a1, *add_name)

        #if m(ast.Call, func=P(ast.Name, id="sum"), args=v.args):
        #    f_idx = self._func_args.index(v.args[0].id)
        #    return None

        if m(ast.Call, func=P(ast.Name,id="exp"), args=v.args) or \
           m(ast.Call, func=P(ast.Attribute, value=P(ast.Name, id="math"), attr="exp"), args=v.args):
            ty_exp_func =  Type.function(ty_float, [ty_float])
            exp_func = Function.get_or_insert(my_module, ty_exp_func, 'exp')
            a1 = self(v.args[0])
            return builder.call(exp_func, [a1])

        if m(ast.Call, func=P(ast.Name,id="sqrt"), args=v.args) or \
           m(ast.Call, func=P(ast.Attribute, value=P(ast.Name, id="math"), attr="sqrt"), args=v.args):
            ty_exp_func =  Type.function(ty_float, [ty_float])
            exp_func = Function.get_or_insert(my_module, ty_exp_func, 'sqrt')
            a1 = self(v.args[0])
            return builder.call(exp_func, [a1])

        if m(ast.Call, func=P(ast.Name, id=v.name), args=v.args):
            ty_func_call = func_types[v.name]
            func_call = Function.get_or_insert(my_module, ty_func_call, v.name)
            args = [self(a) for a in v.args]
            return builder.call(func_call, args)

        #if m(ast.Subscript, value=v.value, slice=v.slice, target_type=numpy.ndarray):
        if m(ast.Subscript, value=v.value, slice=v.slice):
            # Need to access buffer, then compute offset and return index into array
            f_idx = self._func_args.index(v.value.id)
            f_func.args[f_idx].name = v.value.id
            a = f_func.args[f_idx]
            b = builder.gep(a, [Constant.int(ty_int,0),Constant.int(ty_int,2)])
            d = builder.load(b)
            d2 = builder.bitcast(d,Type.pointer(ty_float))
            sv = self(v.slice)
            d3 = builder.gep(d2,[sv])
            e = builder.load(d3)
            return e

        if m(ast.Index, value=P(ast.Name, id=v.id)):
            e = eval(v.id, self._env)
            if isinstance(e, int):
                return Constant.int(ty_int, e)
            return None
        if m(ast.Index, value=P(ast.Num, n=v.n)):
            if isinstance(v.n, int):
                return Constant.int(ty_int, v.n)
            return None
            

        if m(ast.For, target=P(ast.Name, id=v.name),
                      iter=P(ast.Call, func=P(ast.Name, id='range'), args=[P(ast.Num, n=v.range_arg)]),
                      body=v.body):
            pre_header_block = builder.basic_block
            loop_block = f_func.append_basic_block('loop')
            builder.branch(loop_block)

            builder.position_at_end(loop_block)

            loop_variable = v.name
            start_value = Constant.int(ty_int, 0)
            v_phi = builder.phi(ty_int, loop_variable)
            v_phi.add_incoming(start_value, pre_header_block)

            step_value = Constant.int(ty_int, 1)
            next_value = builder.add(v_phi, step_value, 'next')


            self._sym_cache[str(v.name)] = None,v_phi
            self._syms[str(v.name)] = int


            ret = None
            for b in v.body:
                ret = self(b)
            loop_end_block = builder.basic_block
            after_block = f_func.append_basic_block('afterloop')

            # Handle nested loops.
            if ret and isinstance(ret,tuple) and ret[0] == "loop":
                v_phi.add_incoming(next_value, ret[1])
            else: 
                v_phi.add_incoming(next_value, loop_end_block)


            #builder.position_at_end(loop_block)

            end_condition = Constant.int(ty_int, v.range_arg)
            end_compare = builder.icmp(IPRED_ULT, next_value, end_condition, 'loopcond')


            builder.cbranch(end_compare, loop_block, after_block)

            builder.position_at_end(after_block)

            return "loop",after_block

        if m(ast.Return, value=v.e):
            builder.ret(self(v.e))
            return None
    
        if m(ast.Num, n=v.e1, target_type=int):
            return Constant.int(ty_int, v.e1)

        if m(ast.Num, n=v.e1, target_type=float):
            return Constant.real(ty_float, v.e1)

        if m(ast.Name, id=v.e1, target_type=int):
            if self._syms[v.e1] == float:
                print 'Whoa - type assignments not right - symbol is float',v.e1
            try:
                f_idx = self._func_args.index(v.e1)
                f_func.args[f_idx].name = v.e1
                return f_func.args[f_idx]
            except ValueError:
                #return self._sym_cache[v.e1]
                # use the value directly (inlining of the expression value), or load from
                #  stack location
                #try:
                    val,loc = self._sym_cache[v.e1]
                    if val == None:
                        return loc
                    else:
                        return builder.load(loc)
                #except KeyError:
                #    return v.e1
                 

        if m(ast.Name, id=v.e1, target_type=float):
            try:
                f_idx = self._func_args.index(v.e1)
                f_func.args[f_idx].name = v.e1
                if self._syms[v.e1] == int:
                    return builder.sitofp(f_func.args[f_idx], ty_float)
                return f_func.args[f_idx]
            except ValueError:
                #try:
                    val,loc = self._sym_cache[v.e1]
                    ret = loc
                    if val != None:
                        ret =  builder.load(loc)
                    if self._syms[v.e1] == int:
                        return builder.sitofp(ret, ty_float)
                    else:
                        return ret
    
        print '****no match',type(an)
        dump(an)
        

