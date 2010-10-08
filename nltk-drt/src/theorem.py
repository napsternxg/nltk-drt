import subprocess
import select
import nltk
from nltk.sem import Valuation
from nltk.sem.logic import is_indvar
from nltk.inference.mace import MaceCommand
from nltk.inference.prover9 import convert_to_prover9

class Theorem(object):

    BINARY_LOCATIONS = ('/usr/local/bin', '/usr/bin')
    PROVER_BINARY = None
    BUILDER_BINARY = None
    INTERPFORMAT_BINARY = None

    def __init__(self, prover_goal, builder_goal, prover_timeout=60, builder_max_models=500):
        self.prover_goal = prover_goal
        self.builder_goal = builder_goal
        self.prover_timeout = prover_timeout
        self.builder_max_models = builder_max_models
    
    def _find_binary(self, name, verbose=False):
        return nltk.internals.find_binary(name, 
            searchpath=Theorem.BINARY_LOCATIONS, 
            env_vars=['PROVER9HOME'],
            url='http://www.cs.unm.edu/~mccune/prover9/',
            binary_names=[name],
            verbose=verbose)

    def _prover9_input(self):
        return "clear(auto_denials).\nformulas(goals).\n    %s.\nend_of_list.\n\n" % convert_to_prover9(self.prover_goal)

    def _mace_input(self):
        return "formulas(goals).\n    %s.\nend_of_list.\n\n" % convert_to_prover9(self.builder_goal)

    def check(self, verbose=False):
        prover_input = 'assign(max_seconds, %d).\n\n' % self.prover_timeout if self.prover_timeout > 0 else ""
        prover_input += self._prover9_input()

        builder_input = 'assign(end_size, %d).\n\n' % self.builder_max_models if self.builder_max_models > 0 else ""
        builder_input += self._mace_input()

        return self._call(prover_input, builder_input, verbose)

    def _model(self, valuation_str, verbose=False):
        """
        Transform the output file into an NLTK-style Valuation. 
        
        @return: A model if one is generated; None otherwise.
        @rtype: L{nltk.sem.Valuation} 
        """
        valuation_standard_format = self._transform_output(valuation_str, 'standard', verbose)
        
        val = []
        for line in valuation_standard_format.splitlines(False):
            l = line.strip()
            
            if l.startswith('interpretation'):
                # find the number of entities in the model
                num_entities = int(l[l.index('(')+1:l.index(',')].strip())
            
            elif l.startswith('function') and l.find('_') == -1:
                # replace the integer identifier with a corresponding alphabetic character
                name = l[l.index('(')+1:l.index(',')].strip()
                if is_indvar(name):
                    name = name.upper()
                value = int(l[l.index('[')+1:l.index(']')].strip())
                val.append((name, MaceCommand._make_model_var(value)))
            
            elif l.startswith('relation'):
                l = l[l.index('(')+1:]
                if '(' in l:
                    #relation is not nullary
                    name = l[:l.index('(')].strip()
                    values = [int(v.strip()) for v in l[l.index('[')+1:l.index(']')].split(',')]
                    val.append((name, MaceCommand._make_relation_set(num_entities, values)))
                else:
                    #relation is nullary
                    name = l[:l.index(',')].strip()
                    value = int(l[l.index('[')+1:l.index(']')].strip())
                    val.append((name, value == 1))

        return Valuation(val)

    def _transform_output(self, input_str, format, verbose=False):

        if Theorem.INTERPFORMAT_BINARY is None:
            Theorem.INTERPFORMAT_BINARY = self._find_binary('interpformat', verbose)

        if verbose:
            print 'Calling:', Theorem.INTERPFORMAT_BINARY
            print 'Args:', format
            print 'Input:\n', input_str, '\n'

        p = subprocess.Popen([Theorem.INTERPFORMAT_BINARY, format], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             stdin=subprocess.PIPE)
        (stdout, stderr) = p.communicate(input_str)
        
        if verbose:
            print 'Return code:', p.returncode
            if stdout: print 'stdout:\n', stdout, '\n'
            if stderr: print 'stderr:\n', stderr, '\n'
            
        return stdout

    def _call(self, prover_input, builder_input, verbose=False):
        if Theorem.PROVER_BINARY is None:
            Theorem.PROVER_BINARY = self._find_binary('prover9', verbose)

        if Theorem.BUILDER_BINARY is None:
            Theorem.BUILDER_BINARY = self._find_binary('mace4', verbose)
        
        if verbose:
            print 'Calling Prover:', Theorem.PROVER_BINARY
            print 'Prover Input:\n', prover_input, '\n'
            print 'Calling Builder:', Theorem.BUILDER_BINARY
            print 'Builder Input:\n', builder_input, '\n'

        prover = subprocess.Popen([Theorem.PROVER_BINARY], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        builder = subprocess.Popen([Theorem.BUILDER_BINARY], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        prover.stdin.write(prover_input)
        builder.stdin.write(builder_input)
        prover.stdin.flush()
        builder.stdin.flush()

        rlist, wlist, xlist = select.select([builder.stdout, prover.stdout], [], [])
        stdout = rlist[0]

#        polling_object = select.poll()
#        polling_object.register(builder.stdout , select.POLLIN)
#        polling_object.register(prover.stdout , select.POLLIN)
#        stdout, event = polling_object.poll()[0]

        if stdout is prover.stdout: #.fileno():
            if verbose:
                print "Prover finished as first"
            if builder.poll() is None:
                if verbose:
                    print "Builder is still running, terminating..."
                builder.terminate()
            output, error = prover.communicate()
            returncode = prover.poll()
            result = not (returncode == 0)
            if verbose:
                if output: print('output:\t%s' % output)
                if error: print('error:\t%s' % error)
            output = None

        elif stdout is builder.stdout: #.fileno():
            if verbose:
                print "Builder finished as first"
            if prover.poll() is None:
                if verbose:
                    print "Prover is still running, terminating..."
                prover.terminate()
            output, error = builder.communicate()
            returncode = builder.poll()
            result = (returncode == 0)
            if verbose:
                if output: print('output:\t%s' % output)
                if error: print('error:\t%s' % error)
            output = self._model(output, verbose)
  
        if verbose:
            if output: print('output:\t%s' % output)
            if error: print('error:\t%s' % error)

        if verbose:
            print 'Return code:', returncode

        return (result, output)

def main():
    from nltk.sem.logic import LogicParser
    a = LogicParser().parse('p and -p')
    t = Theorem(a, a)
    res = t.check(True)
    print "check returned:", res

def test():
    from nltk.sem.logic import LogicParser
    from nltk.inference.prover9 import Prover9Command 

    g = LogicParser().parse('p and -p')
    #p = Prover9Command(g)
    #out = p.prove(verbose=True)
    #print out
    #print p.proof()
    m = MaceCommand(g)
    out = m.build_model(verbose=True)
    print out
    print m.model('standard')

if __name__ == '__main__':
    main()
