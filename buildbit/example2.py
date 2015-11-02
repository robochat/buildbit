

from bob import Rule as rule
import bob
from sh import touch


r1 = rule('tests/test1.txt',None)
r2 = rule('tests/test2.txt',None)
r3 = rule('tests/test3.txt',None)
r4 = rule('tests/ex1.txt','tests/test*.txt')
r5 = rule('tests/ex%.txt','tests/test%.txt')

def mytouch(self):
    touch(self.targets)

for r in r1,r2,r3,r4,r5:
    r.func = mytouch
    
print rule.calc_build('tests/ex1.txt')


arule = bob.ExplicitRule.rules['tests/ex1.txt']
