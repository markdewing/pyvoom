
# Attemp at pattern matching python AST

class AutoVarInstance(object):
    """Placeholder for binding an AutoVar member."""
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name

    def bind_value(self, name, e):
        self.parent.bind_value(name, e)


class AutoVar(object):
    """
    Tracks member variables for later binding and use.

    Access any member variable and it will return an AutoVarInstance object
    that can bind it to a value later.
    """

    def __getattr__(self,name):
        return AutoVarInstance(self,name)

    def bind_value(self, name, e):
        self.__dict__[name] = e

class Pattern(object):
    """
    Used for nested pattern matching (since named tuples not available)
    """
    def __init__(self, node_type, **kw):
        self._node_type = node_type
        self._keywords = kw


P = Pattern


class Match(object):
    """
    Match patterns in an expression tree.

    Pass the expression to match in the constructor.
    Matching is done with the following methods, which return a boolean:
        __call__ - used most frequently.  First argument is the type
                   of the expression.  Subsequent arguments can be
                   AutoVar members (can be used once match suceeds),
                   values (which match exactly), or tuples (perform
                   a nested match)

    m = Match(e)
    v = AutoVar()
    if m(ast.BinOp, op=ast.Add, left=v.e1, right=v.e2):
        # use v.e1 and v.e2

    # Nested match
    if m(ast.Call, func=P(ast.Name, id="sqrt"), args=v.args):
        # use v.args


    # Matching array of items
    if m(ast.Assign, targets=[P(ast.Name, id=v.t)], value=v.x):
        # use v.t and v.x

    """

    def __init__(self, expr, level=0):
        self.expr = expr
        self.level = level

    def __call__(self, *args, **kw):
        """Match on first argument as an expression type.
           Next arguments bind to expression arguments."""
        match = True
        #print 'type = ',type(self.expr),args[0]

        if len(args) > 0:
            match = isinstance(self.expr,args[0])
        if match == False:
            return False
        if len(args) == 1 and len(kw) == 0:
            return match


        #if len(args)-1 != len(expr_args):
        #    return False

        vars_to_bind = []
        for k,v in kw.iteritems():
            #print 'key = ',k,self.expr.__dict__[k]
            #print 'value = ',v
            if isinstance(v, AutoVarInstance):
                try:
                    vars_to_bind.append( (v, v.name, self.expr.__dict__[k]) )
                except KeyError:
                    print 'Key not found ',k
                    print type(self.expr),dir(self.expr)
                    match=False
            elif isinstance(v, Pattern):
                # do nested match
                #print 'in nested match',k,v
                child_to_match = self.expr.__dict__[k]
                #print '  child to match  = ',self.expr.__dict__[k]
                m = Match(child_to_match, level=1)
                #print 'calling match',v._node_type,v._keywords
                ret = m(v._node_type,**v._keywords)
                #print 'ret from match = ',ret
                if isinstance(ret, tuple):
                    ismatch,v_to_bind = ret
                    vars_to_bind.extend(v_to_bind)
                else:
                    ismatch = ret
                match &= ismatch
            elif isinstance(v, list):
                child_to_match = self.expr.__dict__[k]
                if isinstance(child_to_match, list) and len(v) == len(child_to_match):
                    for a,b in zip(v, child_to_match):
                        m = Match(b, level=1)
                        ret = m(a._node_type, **a._keywords)
                        if isinstance(ret, tuple):
                            ismatch,v_to_bind = ret
                            vars_to_bind.extend(v_to_bind)
                        else:
                            ismatch = ret
                        match &= ismatch
                        if not match:
                            break
                else:
                    match = False
            else:
                #print 'matching field',k,v,self.expr.__dict__[k]
                try:
                    # if an AST field, match on the type
                    #  otherwise match directly
                    if k in self.expr._fields:
                        match = isinstance(self.expr.__dict__[k], v)
                    else:
                        match = self.expr.__dict__[k] == v
                except TypeError:
                    match = self.expr.__dict__[k] == v
                except KeyError:
                    print 'key not found',k
                    match = False
                #print 'match =',match
                if not match:
                    break
     
                
                     
        if not match:
            return match
                

        #for a,e in zip(args[1:], expr_args):
        #    if isinstance(a,tuple):
        #        m = Match(e)
        #        ret = m(*a, level=1)
        #        if isinstance(ret, tuple):
        #            ismatch,vars=ret
        #            vars_to_bind.append( (vars[0],vars[1],vars[2]) )
        #            match &= ismatch
        #        else:
        #            match &= ret 
        #        #match &= m(*a,level=1)
        #    elif isinstance(a, AutoVarInstance):
        #        vars_to_bind.append( (a, a.name, e) )
        #    else:
        #        match &= a == e
        #    if not match:
        #        break
        if match:
            # avoid binding until top-level match succeeds
            if self.level == 0:
                for a,name,e in vars_to_bind:
                    #print 'binding ',name,' in ',args
                    a.bind_value(name,e)
            else:
                return (True,vars_to_bind)

        return match

