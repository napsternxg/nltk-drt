from nltk import load_parser
from eventdrt import EventDrtParser
from util import parse
import nltkfix

def test():
    parser = load_parser('file:../data/eventdrt_test.fcfg', logic_parser=EventDrtParser())
    s1 = "Bill wants a car. Jones needs it. He wants it."
    s2 = "He invites Jones"
    s3 = "Every man wants a car. Bill needs a car"
    drs = parse(parser,s1)
    print(drs)
    drs.draw()

if __name__ == '__main__':
    test()