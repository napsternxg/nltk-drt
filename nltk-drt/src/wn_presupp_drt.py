from temporaldrt import DefiniteDescriptionDRS, DrtParser, DrtTokens,\
    DrtFeatureConstantExpression

class DefiniteDescriptionDRSwithWordNet(DefiniteDescriptionDRS):
    def __init__(self, refs, conds):
        self.wn = WordNetLookup()
        super(DefiniteDescriptionDRSwithWordNet, self).__init__(refs, conds)
        
    def _strict_check (self, presupp_noun, other_cond):
        other_noun = other_cond.function.variable.name
        return (
                presupp_noun == other_noun or 
                self.wn.is_superclasss_of(other_noun, presupp_noun) or 
                (other_cond.is_propername() and (self.wn.is_person(presupp_noun) or self.wn.is_animal(presupp_noun)))
                )
        
    def _non_strict_check(self, presupp_noun, other_noun):
        return (
                (self.wn.is_person(presupp_noun) and self.wn.is_person(other_noun))
                or
                (self.wn.is_animal(presupp_noun) and self.wn.is_animal(other_noun))
               )
        
    def semantic_check(self, individuals, presupp_individuals, strict=True):
        check = {True : self._strict_check, 
                 False: self._non_strict_check}[strict]
        # Strict check - passes if features match and 1) string matching 2) hyponym-hypernym relation, and
        # 3) self.funcname is a person or animal and the antecedent is a proper name
        # Non-strict check: both are people (or animals) and features match
        if isinstance(self.cond, DrtFeatureConstantExpression):
            for individual in individuals:
                if isinstance(individual, DrtFeatureConstantExpression) and check(self.function_name, individual):
                    return True
            return False
        else:
            # If no features are used, we cannot guarantee that the condition we got self.function_name from wasn't an adjective.
            # Likewise, individuals contains not only nouns but also adjectives, and we don't know which are which
            found_noun = False  # We should find at least one noun
            for presupp_individual in presupp_individuals[self.variable]:
                presupp_noun = presupp_individual.function.variable.name
                if not self.wn.is_adjective(presupp_noun):
                    found_noun = True
                    break
            # If we found no noun (that is not also an adjective), ignore the 'is adjective' check for presupposition individuals
            # (in that case, we had probably better ignore this check for 'individuals', too)
            for individual in individuals:
                other_noun = individual.function.variable.name
                if found_noun and self.wn.is_adjective(other_noun): continue
                for presupp_individual in presupp_individuals[self.variable]:
                    presupp_noun = presupp_individual.function.variable.name
                    if found_noun and self.wn.is_adjective(presupp_noun): continue
                    if check (presupp_noun, individual): 
                        return True
            return False
    
class DrtParserWN(DrtParser):

    def handle_PRESUPPOSITION_DRS(self, tok, context):
        
        if tok == DrtTokens.DEFINITE_DESCRIPTION_DRS:
            self.assertNextToken(DrtTokens.OPEN)
            drs = self.handle_DRS(tok, context)
            return DefiniteDescriptionDRSwithWordNet(drs.refs, drs.conds)
        else:
            return DrtParser.handle_PRESUPPOSITION_DRS(self, tok, context)

#--------------------------------------------
from nltk.corpus.reader.wordnet import WordNetCorpusReader
import nltk

class WordNetLookup(object):
    def __init__(self, path='corpora/wordnet'):
        self.path = path
        self.WN = None
    
    def wn(self):
        if not self.WN:
            self.WN = WordNetCorpusReader(nltk.data.find(self.path))
        
    def is_superclasss_of(self, first, second):
        "Is the second noun the superclass of the first one?"
        self.wn()
        # We cannot guarantee it is a noun. By the time we deal with DRSs, this is just a condition, and could have easily
        # come from an adjective (if the user does not provide features for nouns, as we do in our grammar)
        try:
            num_of_senses_first = self._num_of_senses(first)
            self._num_of_senses(second) # just checking that it is a noun
        except: return False
        # At first I wanted to take the first senses of both words, but the first sense is not always the basic meaning of the word, e.g.:
        # S('hammer.n.1').definition: the part of a gunlock that strikes the percussion cap when the trigger is pulled'
        # S('hammer.n.2').definition: 'a hand tool with a heavy rigid head and a handle; used to deliver an impulsive force by striking'
        # Let us iterate over the senses of the first word and hope for the best (since the second word is a more general term,
        # we probably need just its first sense)
        synset_second = self._noun_synset(second, ind=1)
        for i in range(num_of_senses_first):
            #print synset_second, self._noun_synset(first, i).common_hypernyms(synset_second)
            if synset_second in self._noun_synset(first, i).common_hypernyms(synset_second):
                #print "+++ first", first, "second", second, True
                return True
        return False
                
    def is_adjective(self, word):
        try: 
            self._num_of_senses(word, 'a')
            return True
        except: return False
    
    def _noun_synset(self, noun, ind=1):
        self.wn()
        return self.WN.synset("%s.n.%s" % (noun, ind))
    
    def _num_of_senses (self, word, pos='n'):
        self.wn()
        return len(self.WN._lemma_pos_offset_map[word][pos])
    
    def is_person(self, word):
        return self.is_superclasss_of(word, 'person')
    
    def is_animal(self, word):
        return self.is_superclasss_of(word, 'animal')
    
if __name__ == '__main__':
    wn = WordNetLookup()
    
    dog_syn = wn._noun_synset('dog', ind=1)
    canine_syn = wn._noun_synset('canine', ind=1)
    animal_syn = wn._noun_synset('animal', ind=1)
    print "Dog is canine", dog_syn.common_hypernyms(canine_syn) # False !!!
    print "Dog is animal", dog_syn.common_hypernyms(animal_syn) # True
    print "Canine is animal", canine_syn.common_hypernyms(animal_syn) # False
    
    print wn.is_adjective('colour') # True
    print wn.is_adjective('stone')  # True
    print wn.is_adjective('dog')    # False
    