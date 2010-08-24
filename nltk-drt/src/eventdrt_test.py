from nltk import load_parser
from eventdrt import EventDrtParser, AnaphoraResolutionException
from util import parse
import nltkfixtemporal

def test():
    parser = load_parser('file:../data/eventdrt_test.fcfg', logic_parser=EventDrtParser())
    sentences = []
    sentences.append(("He wants a car. Jones needs it.", False))
    sentences.append(("He invites Jones.", False))
    sentences.append(("Jones loves Charlotte but Bill loves her too and he asks himself why", False))
    
    for number, (sentence, is_grammatical) in enumerate(sentences):
        try:
            print(parse(parser, sentence, False))
        except AnaphoraResolutionException, e:
            if not is_grammatical:
                print("%s. *%s (%s)" % (number+1, sentence, e))
            else:
                print("Can't resolve %s" % (sentence))
        except Exception, e:
            print("%s. *%s (%s)" % (number+1, sentence, e))

if __name__ == '__main__':
    test()