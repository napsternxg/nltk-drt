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

def test(parser, logic_parser, cases, compare_resolved = True):
    for number, sentence, expected, error in cases:
        expected_drs = logic_parser.parse(expected)
        try:
            unresolved_drs = parse(parser, sentence, False)
            resolved_drs = unresolved_drs.resolve()
            if error:
                print("%s. !error: expected %s" % (number, str(error)))
            else:
                if (compare_resolved and resolved_drs == expected_drs) or (not compare_resolved and unresolved_drs == expected_drs):
                    print("%s. %s (%s)" % (number, sentence, resolved_drs))
                else:
                    print("%s. !comparison failed %s != %s)" % (number, resolved_drs, expected_drs))
        except Exception, e:
            if error and isinstance(e, error):
                if unresolved_drs == expected_drs:
                    print("%s. *%s (%s)" % (number, sentence, e))
                else:
                    print("%s. !comparison failed %s != %s)" % (number, resolved_drs, expected_drs))
            else:
                print("%s. !unexpected error: %s" % (number, e))
