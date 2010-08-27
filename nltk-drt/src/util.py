class ReverseIterator:
    def __init__(self, sequence):
        self.sequence = sequence
    def __iter__(self):
        i = len(self.sequence)
        while i > 0:
            i = i - 1
            yield self.sequence[i]

def parse(parser, text, show_interim = True):
    sentences = text.split('.')
    drs = None
    for sentence in sentences:
        sentence = sentence.lstrip()
        if sentence:
            new_words = []
            for word in sentence.split():
                if "'" in word:
                    parts = word.split("'")
                    new_words.append(parts[0])
                    if parts[1]:
                        new_words.append(parts[1])
                else:
                    new_words.append(word)

            trees = parser.nbest_parse(new_words)
            new_drs = trees[0].node['SEM'].simplify()
            if show_interim:
                print(new_drs)
            if drs:
                drs = (drs + new_drs).simplify()
            else:
                drs = new_drs

    if show_interim:
        print drs
    return drs

def test(parser, logic_parser, cases):
    for number, sentence, expected, error in cases:
        expected_drs = logic_parser.parse(expected)
        drs_list = []
        try:
            drs_list.append(parse(parser, sentence, False))
            drs_list.append(drs_list[-1].resolve())
            drs_list.append(drs_list[-1].resolve())
            if error:
                print("%s. !error: expected %s" % (number, str(error)))
            else:
                if drs_list[-1] == expected_drs:
                    print("%s. %s %s" % (number, sentence, drs_list[-1]))
                else:
                    print("%s. !comparison failed %s != %s" % (number, drs_list[-1], expected_drs))
        except Exception, e:
            if error and isinstance(e, error):
                if drs_list[-1] == expected_drs:
                    print("%s. *%s %s (%s)" % (number, sentence, drs_list[-1],  e))
                else:
                    print("%s. !comparison failed %s != %s" % (number, drs_list[-1], expected_drs))
            else:
                print("%s. !unexpected error: %s" % (number, e))
