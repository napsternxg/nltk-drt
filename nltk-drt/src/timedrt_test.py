import nltkfix

from nltk import load_parser
from nltk.sem.drt import AbstractDrs

from timedrt import TemporalDrtParser, resolve

def gr(s, recursive=False):
    return []

AbstractDrs.get_refs = gr


if __name__ == "__main__":

  parser = load_parser('file:../data/tenseaspect.fcfg', logic_parser=TemporalDrtParser())
  trees = parser.nbest_parse('Angus will not own a dog'.split())
  parse = resolve(trees[0].node['SEM'].simplify())
  print parse
  parse.draw()

