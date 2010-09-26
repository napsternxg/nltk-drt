import nltk.inference.prover9 as prover9
import nltk.inference.mace as mace
import subprocess
import nltk.inference.api as api
from threading import Thread

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

    def isrunning(self):
        return hasattr(self, 'process')

    def terminate(self):
        if self.process.poll() is None:
            self.process.terminate()

class Prover9(Prover9Parent, prover9.Prover9):
    def __init__(self, timeout=60):
        prover9.Prover9.__init__(self, timeout)

class Mace(Prover9Parent, mace.Mace):
    def __init__(self, end_size=30):
        mace.Mace.__init__(self, end_size)

class Prover(Thread):
    """Wrapper class for Prover9"""
    def __init__(self,expression):
        Thread.__init__(self)
        self.prover = prover9.Prover9Command(expression, None, None, Prover9())
        self.result = None
    
    def run(self):
        self.result = self.prover.prove(False)
        
    
class Builder(Thread):
    """Wrapper class for Mace"""
    def __init__(self,expression):
        Thread.__init__(self)              
        self.builder = mace.MaceCommand(None,[expression],None, Mace())
        self.result = None 
    
    def run(self):
        self.result = self.builder.build_model(False)
