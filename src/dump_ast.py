
# experiments with Python ast

import ast
import sys


def dump(an,indent=0):
    istr = ' '*indent
    for an1 in ast.iter_child_nodes(an):
        print istr,type(an1)
        #for an2 in ast.iter_child_nodes(an1):
        #    print '   ',type(an2),an2
        for an3 in ast.iter_fields(an1):
            print istr + '   ',an3[0],an3[1]
        if hasattr(an1,'target_type'):
            print istr + '   target_type = ',an1.target_type
        dump(an1,indent+1)


def dump_ast(fname):
    ff = open(fname,'r')
    lines = [l for l in ff.readlines()]
    ff.close()
    an = ast.parse(''.join(lines))
    dump(an)

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print 'Usage: dump_ast <file name>'
        sys.exit(1)
    dump_ast(sys.argv[1])
