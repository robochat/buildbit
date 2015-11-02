

from bob import Rule as rule
import bob
from sh import touch


@rule('tests/test1.txt',None)
@rule('tests/test2.txt',None)
@rule('tests/test3.txt',None)
@rule('tests/ex1.txt','tests/test*.txt')
@rule('tests/ex%.txt','tests/test%.txt')
def mytouch(self):
    touch(self.targets)


print rule.calc_build('tests/ex1.txt')


arule = bob.ExplicitRule.rules['tests/ex1.txt']
