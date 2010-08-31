from featuredrt import DrtParser
from temporaldrt import DrtProperNameApplicationExpression, DrtAbstractVariableExpression, DRS
from nltk.sem.logic import Variable

def main():
    parser = DrtParser()
    drs_string = "DRS([],[(([x,z2,e],[Jones{sg,m}(x), car{sg,n}(z2), own(e), AGENT(e,x), THEME(e,z2)]) | ([x,e],[PRO{sg,m}(x), commute(e), AGENT(e,x)]))])"
    drs = parser.parse(drs_string)
    print(drs)

    class Combinator(object):
        def __init__(self, class_name):
            self.class_name = class_name
        def __call__(self, *args):
            print "Combinator %s(%s)" % (self.class_name.__name__, args)
            if len(args) == 2:
                return self.class_name(args[0],args[1])
            else:
                raise Exception

    def drs_combinator(*args):
        print "drs_combinator %s" % (str(args))
        if len(args) == 2:
            if isinstance(args[1], Variable):
                args[0].refs.append(args[1])
            else:
                args[0].conds.append(args[1])
            return args[0]
        else:
            raise Exception

    class Function():
        def __init__(self, substitutions):
            self.substitutions = substitutions

        def __call__(self, expr):
            print "function", type(expr), expr
            if isinstance(expr, DrtAbstractVariableExpression) or isinstance(expr, Variable):
                return expr
            elif isinstance(expr, DRS):
                res = expr.visit(self, drs_combinator, expr.__class__([],[]))
                if expr in self.substitutions:
                    print "found expresson for substitution", res
                    self.substitutions[expr](res)
                    print "substitution result", res

                return res
                
            else:
                return expr.visit(self, Combinator(expr.__class__), None)
    
    readings = drs.readings()
    function = Function(readings[0].substitutions)
    print function(drs)
    print drs
    #print function.triggers
if __name__ == '__main__':
    main()