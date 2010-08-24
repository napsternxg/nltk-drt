
def parse(parser, text, show_interim = True):
    sentences = text.split('.')
    drs = None
    for sentence in sentences:
        sentence = sentence.lstrip()
        if sentence:
            words = sentence.split()
            new_words = []
            for word in words:
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
    return drs.resolve()