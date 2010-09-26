import nltk.inference.prover9 as prover9
import nltk.inference.mace as mace
import subprocess
import nltk.inference.api as api

class Prover9Parent(prover9.Prover9Parent):
    """
    A common class extended by both L{Prover9} and L{Mace <mace.Mace>}.
    It contains the functionality required to convert NLTK-style
    expressions into Prover9-style expressions.
    """
    
    def _call(self, input_str, binary, args=[], verbose=False):
        """
        Call the binary with the given input.
    
        @param input_str: A string whose contents are used as stdin.
        @param binary: The location of the binary to call
        @param args: A list of command-line arguments.
        @return: A tuple (stdout, returncode)
        @see: L{config_prover9}
        """
        if verbose:
            print 'Calling:', binary
            print 'Args:', args
            print 'Input:\n', input_str, '\n'
        
        # Call prover9 via a subprocess
        cmd = [binary] + args
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             stdin=subprocess.PIPE)
        (stdout, stderr) = self.process.communicate(input_str)
        
        if verbose:
            print 'Return code:', self.process.returncode
            if stdout: print 'stdout:\n', stdout, '\n'
            if stderr: print 'stderr:\n', stderr, '\n'
            
        return (stdout, self.process.returncode)

    def terminate(self):
        self.process.terminate()

class Prover9(Prover9Parent, prover9.Prover9):
    pass

class Mace(Prover9Parent, mace.Mace):
    pass

class Prover9Command(prover9.Prover9Command):
    """
    A L{ProverCommand} specific to the L{Prover9} prover.  It contains
    the a print_assumptions() method that is used to print the list
    of assumptions in multiple formats.
    """
    def __init__(self, goal=None, assumptions=None, timeout=60, prover=None):
        """
        @param goal: Input expression to prove
        @type goal: L{logic.Expression}
        @param assumptions: Input expressions to use as assumptions in
            the proof.
        @type assumptions: C{list} of L{logic.Expression}
        @param timeout: number of seconds before timeout; set to 0 for
            no timeout.
        @type timeout: C{int}
        @param prover: a prover.  If not set, one will be created.
        @type prover: C{Prover9}
        """
        if not assumptions:
            assumptions = []
        
        if prover is not None:
            assert isinstance(prover, Prover9)
        else:
            prover = Prover9(timeout)
         
        api.BaseProverCommand.__init__(self, prover, goal, assumptions)

class MaceCommand(mace.MaceCommand):
    pass