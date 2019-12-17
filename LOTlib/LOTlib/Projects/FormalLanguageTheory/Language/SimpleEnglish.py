from FormalLanguage import FormalLanguage
from LOTlib.Grammar import Grammar
from pickle import load

class SimpleEnglish(FormalLanguage):
    """
    A simple English language with a few kinds of recursion all at once
    """

    def __init__(self):
        self.grammar = Grammar(start='S')
        self.grammar.add_rule('S', '%s%s', ['NP', 'VP'], 4.0)
        self.grammar.add_rule('NP', 'd%sn', ['AP'], 1.0)
        self.grammar.add_rule('NP', 'dn', None, 1.0)
        self.grammar.add_rule('NP', 'n', None, 2.0)
        self.grammar.add_rule('AP', 'a%s', ['AP'], 1.0)
        self.grammar.add_rule('AP', 'a', None, 3.0)

        #self.grammar.add_rule('NP', '%s%s', ['NP', 'PP'], 1.0) # a little ambiguity
        #self.grammar.add_rule('VP', '%s%s', ['VP', 'PP'], 1.0)
        #self.grammar.add_rule('PP', 'p%s', ['NP'], 1.0)

        self.grammar.add_rule('VP', 'v', None, 2.0) # intransitive
        self.grammar.add_rule('VP', 'v%s', ['NP'], 1.0) # transitive
        self.grammar.add_rule('VP', 'vt%s', ['S'], 1.0) # v that S

        #self.grammar.add_rule('S', 'i%sh%s', ['S', 'S'], 1.0)  # add if S then S grammar -- seems hard, and unnattural to get so many

    def terminals(self):
        return list('dnavt')

    def all_strings(self):
        for g in self.grammar.enumerate():
            yield str(g)

# just for testing
if __name__ == '__main__':
    language = SimpleEnglish()
    print language.sample_data(100000)
