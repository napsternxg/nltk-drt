from util import Tester
import presuppositions
from presuppositions import DrtParser

# Nltk fix
import nltkfixtemporal_emmas
from nltk.sem.drt import AbstractDrs
def gr(s, recursive=False):
    return []
AbstractDrs.get_refs = gr

if __name__ == '__main__':
    tester = Tester('file:../data/grammar.fcfg', DrtParser)
    #presuppositions.presuppositions_sentences(tester)
    #presuppositions.anaphora_main(tester)
    presuppositions.alex_anaphora_test_main()