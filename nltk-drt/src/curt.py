import sys
import random
from test import BK
from util import Tester
from temporaldrt import DrtParser
from inference import AdmissibilityOuput, ConsistencyOuput, InformativityOuput

class Curt(object):
    INADMISSIBLE = ["That's Greek to me", "Do you get my drift?", "Now, hold your horses!", "Well, I dunno...", "Neither rhyme nor reason."]
    INCONSISTENT = ["I don't believe that!", "Nice try!", "That's a switch!", "Don't try to butter me up!", "I smell a rat.", "Tell it to the marines!"]
    UNINFORMATIVE = ["I know that already!", "Whatever!", "You ain't seen nothing yet!", "Hey, that's an oldie.", "Betcha don't know.", "It's all one to me "]
    OK = ["Nice to know", "OK", "Go on!", "Go ahead!", "No problem!", "Do your thing!", "No kiddin'?", "Really?", "Is that so?", "That's more like it", "What are you driving at?", "C'mon, shake a leg!", "Well, that's the way the cookie crumbles.", "Spill the beans!",  "While you live, tell truth and shame the Devil!"]
    GOODBYE = ["See ya!", "Nice talking to you!", "Bye!", "Take care!"]
    def __init__(self, grammar_file='file:../data/grammar.fcfg', logic_parser=DrtParser, background=None):
        self.tester = Tester(grammar_file, logic_parser)
        self.background = background
        self.discourse = None
        
    def randomize(self, option_list):
        return option_list[random.randint(0, len(option_list)-1)]

    def inadmissible(self):
        return self.randomize(Curt.INADMISSIBLE)

    def inconsistent(self):
        return self.randomize(Curt.INCONSISTENT)
        
    def uninformative(self):
        return self.randomize(Curt.UNINFORMATIVE)

    def ok(self):
        return self.randomize(Curt.OK)
    
    def goodbye(self):
        return self.randomize(Curt.GOODBYE)
    
    def respond(self, s, human_readable):
        if isinstance(s, AdmissibilityOuput):
            return "%s(%s)" % (self.inadmissible(), "inadmissible" if human_readable else "")
        elif isinstance(s, ConsistencyOuput):
            return "%s(%s)" % (self.inconsistent(), "inconsistent" if human_readable else "")
        elif isinstance(s, InformativityOuput):
            return "%s(%s)" % (self.uninformative(), "uninformative" if human_readable else "")

    def process(self, utterance, human_readable=False, verbose=False):
        if self.discourse is None:
            self.discourse = self.tester.parse(utterance, utter=True)
        else:
            expression = self.tester.parse_new(self.discourse, utterance)
            inferences, errors = self.tester.interpret_new(self.discourse, expression, background=self.background, verbose=verbose)
            if not inferences:
                out = []
                for reading, error in errors:
                    if verbose:
                        print error
                    out.append(self.respond(error, human_readable))
                return ", ".join(out)
            else:
                self.discourse = (self.discourse + expression).simplify()

        return self.ok()
        
    def __str__(self):
        return str(self.discourse)

def main():
    show_model = False
    explicit = False
    curt = Curt(background=BK)
    while True:
        s = raw_input("What say you? ")
        if s == "bye":
            print curt.goodbye()
            return
        elif s == "m":
            show_model = False if show_model else True
            print "display models: %s" % ("on" if  show_model else "off")
        elif s == "e":
            explicit = False if explicit else True
            print "explicit errors: %s" % ("on" if  explicit else "off")
        else:
            print "You say:\t%s" % s
            try:
                print "Curt says:\t%s" % curt.process(s)
            except ValueError as e:
                print "Error: %s" % e
                
            if show_model:
                print "Model: %s" % str(curt)

def test_curt():
    input = ["Mia is away", "Angus is out", "Mia is not away", "Mia is away", "If Mia is away Angus is out", ]
    curt = Curt(background=BK)
    for i in input:
        print i
        print curt.process(i, True)

def test():
    tester = Tester('file:../data/grammar.fcfg', DrtParser)
    tester.interpret("Mia is away","Mia is away", bk=BK, verbose=True, test=False)

if __name__ == "__main__":
    test_curt()