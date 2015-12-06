#!/usr/bin/env python
"""module of unit tests for fpmatch module"""

import unittest2 as unittest
import fpmatch


class TestFilter(unittest.TestCase):
    def setup(self):
        self.paths = ['tests/test1','tests/test2.txt','tests/test3',
                      'tests/test/test4.txt',
                      'test B/test5','test B/ex1.txt','test B/test5.c',
                     ]
        #self.paths += ['test*/a','test C/file*.txt','test C/file%.txt']
    
    def test_direct_match(self):
        for pat in self.paths:
            res=fpmatch.filter(self.paths,pat=pat)
            self.assertTrue(res == pat)
        
    def test_no_match(self):
        for pat in [???]:
            res=fpmatch.filter(self.paths,pat=pat)
            self.assertTrue(res == pat)
        
    def test_wildcard_match(self):
                
    def test_wildcard_no_match(self):
        
    def test_wildcards_with_subdirectories(self):
        
    def test_pattern_match(self):
        
        retrieve_stem
        
    def test_pattern_no_match(self):
        
        
    def test_pattern_with_subdirectories(self):
        
    def test_general_pattern_match(self):
        
    
    def teardown(self):
        pass



#is this a bug?
assert fpmatch.strip_specials('test[]]time') != 'test]time' #not sure this is a bug though
#question
fpmatch.strip_specials('test[abcd].txt') == 'test.txt' #this is what we want isn't it?
#but
fpmatch.strip_specials('test[*].txt') == 'test.txt' # is this really what we want?


#strange cases - test[!].txt is treated as a literal
#test[]]test becomes test[]]test as we expect but
#test[!]test[]test becomes test[^]test[]\\]test
#think that it is logical but can be tricky. Rule is that can include closing bracket in
#char list if it is the first entry only but there is a corner case if there is no closing 
#bracket later in the string.