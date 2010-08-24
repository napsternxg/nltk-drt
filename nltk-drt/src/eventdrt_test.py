from nltk import load_parser
from eventdrt import EventDrtParser, AnaphoraResolutionException
from util import parse
import nltkfixtemporal

def test():
    parser = load_parser('file:../data/eventdrt_test.fcfg', logic_parser=EventDrtParser())
    sentences = [
    ("He wants a car. Jones needs it.", False),
    ("He invites Jones.", False),
    ("Jones loves Charlotte but Bill loves her and he asks himself.", True),
    ("Jones loves Charlotte but Bill loves her and he asks him.", True),
    ("Jones loves Charlotte but Bill loves her and himself asks him.", False),
    ("Jones likes this picture of himself.", True),
    ("Jones likes this picture of him.", True),
    ("Bill likes Jones's picture of himself", True),
    ("Bill likes Jones's picture of him", True),
    ("Bill's car walks", True)
    ]

    sentences = []
    for number, (sentence, is_grammatical) in enumerate(sentences):
        try:
            print("%s. %s %s" % (number+1, sentence, parse(parser, sentence, False)))
            if not is_grammatical:
                print("Error!")
        except AnaphoraResolutionException, e:
            if not is_grammatical:
                print("%s. *%s (%s)" % (number+1, sentence, e))
            else:
                print("Can't resolve %s" % (sentence))
        except Exception, e:
            print("%s. *%s (%s)" % (number+1, sentence, e))

    print(parse(parser, "Bill's car walks"))

if __name__ == '__main__':
    test()