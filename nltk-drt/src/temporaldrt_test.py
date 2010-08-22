import nltkfixtemporal

from nltk import load_parser
from nltk.sem.drt import AbstractDrs

from temporaldrt import DrtParser

def gr(s, recursive=False):
    return []

AbstractDrs.get_refs = gr

if __name__ == "__main__":
    parser = load_parser('file:../data/tenseaspect.fcfg', logic_parser=DrtParser())
    trees = parser.nbest_parse('Angus will not own a dog'.split())
    parse = trees[0].node['SEM'].simplify().resolve()
    print parse
    parse.draw()
