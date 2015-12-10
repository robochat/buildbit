#!/usr/bin/env python
"""module of unit tests for buildbit system. Rather than testing the rules
individually (see test_rules). This module aims to test the build_calc()
method and the interactions between sets of rules."""

#start with example2.py as a complicated set of all of the types of rules
#test the buildcalc of various targets
#actually build various things and test how the buildcalc changes.

import unittest2 as unittest
import bob
import os, shutil


class BaseTestBuilds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        #empty all rule registries and clear all caches
        reload(bob)
        #bob.Rule.drop_rules()
        #bob.Rule.reset_cache()
        
        #import module which uses all of the Rule classes at least once.
        import setup_test_buildbit
        cls.tf = setup_test_buildbit
        cls.outpath = cls.tf.outpath
        cls.outdir = cls.tf.outpath.strip('/')
        
        #make sure that test output directory doesn't exist
        if os.path.isdir(cls.outdir):
            shutil.rmtree(cls.outdir)
            
    @classmethod
    def tearDownClass(cls):
        #unload setup_test_buildbit module?
        
        #remove rules from registries and clear caches
        reload(bob)
        #bob.Rule.drop_rules()
        #bob.Rule.reset_cache()
        
        #remove test directory
        if os.path.isdir(cls.outdir):
            shutil.rmtree(cls.outdir)
        


class TestCleanBuilds(BaseTestBuilds):
    """test that various targets' buildsequences are correct for
    a fresh build (no files in the directory)"""
        
    def test_dir_creation(self):
        bseq = bob.Rule.calc_build(self.outdir)
        self.assertEqual(bseq,[self.tf.r0])
        self.assertEqual(bseq,[bob.ExplicitRule.rules[self.outdir]])
        self.assertEqual(bseq,[bob.Rule.get(self.outdir)])
        
    def test_dirA_creation(self):
        bseq = bob.Rule.calc_build(self.outpath+'A')
        self.assertEqual(bseq,[self.tf.r0, self.tf.r1])
        self.assertEqual(bseq,[bob.ExplicitRule.rules[self.outdir],bob.ExplicitRule.rules[self.outpath+'A']])
        self.assertEqual(bseq,[bob.Rule.get(self.outdir),bob.Rule.get(self.outpath+'A')])
    
    def test_dirB_creation(self):
        bseq = bob.Rule.calc_build(self.outpath+'B')
        erules = bob.ExplicitRule.rules
        self.assertEqual(bseq,[self.tf.r0,self.tf.r2])
        self.assertEqual(bseq,[erules[self.outdir],erules[self.outpath+'B']])
        self.assertEqual(bseq,[bob.Rule.get(self.outdir),bob.Rule.get(self.outpath+'B')])

    def test_explicit_rules_order_only_r3(self):
        bseq = bob.Rule.calc_build(self.outpath+'A/test1.c')
        tf = self.tf
        erules = bob.ExplicitRule.rules
        R = bob.Rule
        out = self.outpath
        self.assertEqual(bseq,[tf.r0,tf.r1,tf.r3])
        self.assertEqual(bseq,[erules[self.outdir],erules[out+'A'],erules[out+'A/test1.c']])
        self.assertEqual(bseq,[R.get(self.outdir),R.get(out+'A'),R.get(out+'A/test1.c')])
        
    def test_explicit_rules_order_only_r4(self):
        bseq = bob.Rule.calc_build(self.outpath+'A/test2')
        tf = self.tf
        erules = bob.ExplicitRule.rules
        R = bob.Rule
        out = self.outpath
        self.assertEqual(bseq,[tf.r0,tf.r1,tf.r4])
        self.assertEqual(bseq,[erules[self.outdir],erules[out+'A'],erules[out+'A/test2']])
        self.assertEqual(bseq,[R.get(self.outdir),R.get(out+'A'),R.get(out+'A/test2')])

    def test_r5_overwritten(self):
        bseq = bob.Rule.calc_build(self.outpath+'A/test3.txt')
        #the original rule r5 was overwritten by r11
        tf = self.tf
        erules = bob.ExplicitRule.rules
        R = bob.Rule
        out = self.outpath
        self.assertNotEqual(bseq[-1],tf.r5)
        self.assertEqual(bseq,[R.get(self.outdir),R.get(out+'A'),R.get(out+'B'),R.get(out+'A/test3.txt')])
        rw1 = tf.r11.explicit_rules[0] #getting into implementation details
        self.assertEqual(bseq,[tf.r0,tf.r1,tf.r2,rw1])
        self.assertEqual(bseq,[erules[self.outdir],erules[out+'A'],erules[out+'B'],rw1])
        
    def test_explicit_rules(self):
        tf = self.tf
        targets = [self.outpath+'A/test%d.c' %i for i in range(4,20)]
        for target in targets:
            bseq = bob.Rule.calc_build(target)
            self.assertEqual(bseq,[tf.r0,tf.r1,tf.r6])
        self.assertEqual(tf.r6.targets,targets)
        
    def test_rule_w_prerequisites(self):
        tf = self.tf
        bseq = bob.Rule.calc_build(self.outpath+'A/ex1.txt')
        rw1 = tf.r11.explicit_rules[0]
        rw1b = bob.Rule.get(self.outpath+'A/test3.txt')
        for rw in rw1,rw1b:
            self.assertEqual(bseq,[tf.r0,tf.r1,tf.r4,tf.r2,rw1,tf.r7])
            
    def test_ManyRules(self):
        tf = self.tf
        targets = [self.outpath+'A/foo{0}'.format(i) for i in range(10)]
        for target,trule in zip(targets,tf.r8): 
            bseq = bob.Rule.calc_build(target)
            self.assertEqual(bseq,[tf.r0,tf.r1,trule])
            bseq2 = trule.calc_build()
            self.assertEqual(bseq,bseq2)
            
    def test_wildcard_prereq(self):
        tf = self.tf
        target = self.outpath+'B/contentsA.txt'
        bseq = bob.Rule.calc_build(target)
        bseq2 = tf.r9.calc_build()
        self.assertEqual(bseq,bseq2)
        rw1 = tf.r11.explicit_rules[0]
        self.assertEqual(set(bseq),set([tf.r0,tf.r1,tf.r2,tf.r3,tf.r4,tf.r6,tf.r7,rw1,tf.r9]+tf.r8))
        
    def test_phony(self):
        tf = self.tf
        pass # a difficult one to test


"""        
    def test_wildcard_target(self):
        
    def test_wildcard_target2(self):
    
    def test_wildcard_target3(self):
        
    def test_general_pattern_rule(self):
        
    def test_pattern_rule(self):
        
    def test_intemediates(self):
        
    def test_pattern_rule_best_match(self):
        
    def test_pattern_rule_with_wildcards(self):
        
    def test_explicit_to_metarules(self):
        
##create a general pattern rule - can match to requested prerequisites in sub-directories too.
r10 = rule('%.o','%.c',func='touch {targets}') # using command string directly
assert isinstance(r10,bob.PatternRule)

#buildbit will create intemediate files (unlike make though it doesn't yet delete them)
rule(outpath+'result',[outpath+'A/test{0}.o'.format(i) for i in [1]+range(4,20)]).func=myls
#because r2 is a shared rule, buildbit will only run the it once despite multiple requests for its targets.

##pattern rule
rule(outpath+'test%.o',outpath+'A/test%.c',order_only=[outpath+'B']).func=makefile #pattern rule

#buildbit will use the pattern rule with the closest match
rule(outpath+'result2',[outpath+'test{0}.o'.format(i) for i in range(4,20)],func=myls)

##pattern rule with wildcards
r15 = rule(outpath+'%/*est%.final',outpath+'%/test%.*',func=makefile)
        
    
class TestReBuilds(TestBuilds):
    ""test that rebuilds are calculated correctly/efficiently""

        
"""