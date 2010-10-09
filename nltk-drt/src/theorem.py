import subprocess
import nltk
from nltk.sem import Valuation
from nltk.sem.logic import is_indvar
from nltk.inference.mace import MaceCommand
from nltk.inference.prover9 import convert_to_prover9
from threading import Thread

class Communicator(Thread):
    def __init__(self, process, input=None):
        Thread.__init__(self)
        self.process = process
        self.input = input
    
    def run(self):
        try:
            self.result = self.process.communicate(self.input)
        except OSError:
            pass

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
        return "clear(auto_denials).\n%s" % self._input(self.prover_goal)

    def _mace_input(self):
        return self._input(self.builder_goal)
    
    def _input(self, goal):
        return "formulas(goals).\n    %s.\nend_of_list.\n\n" % convert_to_prover9(goal)

    def check(self, verbose=True):
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

        prover_process = subprocess.Popen([Theorem.PROVER_BINARY], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

#        stdout, stderr = prover_process.communicate(prover_input)
#        returncode = prover_process.poll()
#        result = not (returncode == 0)
#        output = None
#        print "prover done"
        
        builder_process = subprocess.Popen([Theorem.BUILDER_BINARY], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
#
#        stdout, stderr = builder_process.communicate(builder_input)
#        returncode = builder_process.poll()
#        result = (returncode == 0)
#        output = self._model(stdout, verbose)
#        
#        print "builder done"

        prover_thread = Communicator(prover_process, prover_input)
        builder_thread = Communicator(builder_process, builder_input)
        
        prover_thread.start()
        builder_thread.start()

        while prover_thread.is_alive() and builder_thread.is_alive():
            pass

        if verbose:
            print "Prover %s, Builder %s " % ("done" if not prover_thread.is_alive() else "running", "done" if not builder_thread.is_alive() else "running")

        if not prover_thread.is_alive():
            stdout, stderr = prover_thread.result
            returncode = prover_process.poll()
            result = not (returncode == 0)
            output = None
            if builder_process.poll() is None:
                try:
                    builder_process.terminate()
                except OSError:
                    pass
                if verbose:
                    print "builder is still running, terminating..."

        elif not builder_thread.is_alive():
            stdout, stderr = builder_thread.result
            returncode = prover_process.poll()
            result = (returncode == 0)
            output = self._model(stdout, verbose)
            if prover_process.poll() is None:
                try:
                    prover_process.terminate()
                except OSError:
                    pass
                if verbose:
                    print "prover is still running, terminating..."
  
        if verbose:
            if stdout: print('output:\t%s' % stdout)
            if stderr: print('error:\t%s' % stderr)
            print 'return code:', returncode

        return (result, output)

def main():
    from nltk.sem.logic import LogicParser
    a = LogicParser().parse('(exists n (exists z128 (exists s (exists x (exists z138 (((((((((Mia = x) & husband(z128)) & own(s)) & AGENT(s,x)) & PATIENT(s,z128)) & overlap(n,s)) & all s0140(((married(s0140) & THEME(s0140,x)) & overlap(n,s0140)) -> exists t0135 (exists e ((((earlier(t0135,n) & walk(e)) & AGENT(e,z138)) & include(t0135,e)) & event(e)) & time(t0135)))) & (Angus = z138)) & individual(z138)) & individual(x)) & state(s)) & individual(z128)) & time(n)) & ((((all x all y all z ((include(x,y) & include(z,y)) -> overlap(x,z)) & (all x all y all z ((earlier(x,y) & earlier(y,z)) -> earlier(x,z)) & all x all y (earlier(x,y) -> -(overlap(x,y))))) & all t all s (((married(s) & THEME(s,x)) & overlap(t,s)) -> exists x (exists y ((POSS(y,x) & husband(y)) & individual(y)) & individual(x)))) & all s all x all y (((own(s) & AGENT(s,x)) & PATIENT(s,y)) -> POSS(y,x))) & all t all x all y ((POSS(y,x) & husband(y)) -> exists s (((married(s) & THEME(s,x)) & overlap(t,s)) & state(s)))))')
    t = Theorem(a, a, 120, 60)
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
