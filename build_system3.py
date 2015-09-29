#!/usr/bin/env python2
"""a simple build system inspired by gnu make"""

from orderedset import OrderedSet
#import pathlib
import os.path
import warnings
import glob
import itertools
import inspect
from collections import Iterable
from types import StringTypes
from sys import maxint

import fpmatch

def checksingleinput(val):
    """checks that input is not a sequence"""
    if isinstance(val,StringTypes): pass
    elif isinstance(val,Iterable): raise InputError("input should not be a sequence: %r" %val)
    return val

def checkseq(val):
    """replaces None with an empty tuple and wraps
    non-iterable values into a tuple too."""
    if not val: val = tuple()
    elif isinstance(val,StringTypes): val = (val,)
    elif not isinstance(val,Iterable): val = (val,)
    return val

def dedup(seq):
    """deduplicate a list while keeping the original order"""
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if not (x in seen or seen_add(x))]

def argmax(lst):
  return lst.index(max(lst))

def argmin(lst):
  return lst.index(min(lst))

@memorize
get_mtime(fpath):
    os.path.getmtime(fpath)
    
class Make(object):
    """Acts as a base class and contains the get() method for finding the best match
    for a target/req from the child classes."""
    searchorder = [ExplicitRule,WildSharedRule,WildRule,PatternRule] #custom child classes should add themselves to this list
                
    @class_method
    def get(cls,target,default=None):
        """Searches for rule with matching target. Pattern matching is performed 
        and the best match is returned. So target must be explicit. If the target
        rule is not found, returns default."""
        for cls in cls.children:
            rule = cls.get(target,default)
            if rule != default:
                break
        return rule 
        #InputError("No target found for %r" %target)
                
    @class_method
    def calc_build_order(cls,target):
        """calculate the build order to get system up to date"""    
        toprule = cls.get(target)
        build_order = toprule.calc_build()
        return build_order

    def build(self):
        raise NotImplementedError
        
    def calc_build_order(self):
        raise NotImplementedError



# Explicit/Shared rules
#-------------------------------------------------------------------------------

## rules where those with multiple targets are still only run once.
##------------------------------------------------------------------------------

class ExplicitRule(Make):
    """A multiple target, multiple prerequisite rule that will only run
    once no matter how many of the specified targets are required. There
    shouldn't be any wildcards in the targets and reqs lists. reqs can
    contain duplicates and be order dependent though.
    
    The class can also be used as a decorater????
    """
    rules = {} #target:rule dict
    
    @class_method
    def get(cls,target,default=None):
        """Find any explicit rules for the given target."""
        return cls.rules.get(target,default)
    
    def __init__(targets,reqs,order_only=None,func=None,PHONY=False):
        """targets - list of targets
        reqs - seq of prerequisites
        order_only - seq of order only prerequisites
        func - a function that should take one or no arguments. Will be
            passed this class instance when run in order to have access
            to its attributes
        """
        self.targets = checkseq(targets)
        self.PHONY = PHONY
        self.allreqs = checkseq(reqs)
        self.reqs = dedup(self.allreqs)
        self.order_only = checkseq(order_only)
        if func: self.func = func
        self.updated_only = self.updated_only()
        
        #Add self to Make registry
        for target in self.targets:
            if target in self.rules:
                warnings.warn('Make takes the last defined rule for each target. Overwriting the rule for %r' %target)
            self.rules[target] = self
    
    def build(self):
        """run recipe"""
        if hasattr(self,'func'):
            func_argspec = inspect.getargspec(self.func)
            func_args = func_argspec[0]
            if len(func_args)==1:
                self.func(self)
            elif len(func_args)==0:
                self.func()
            else:
                raise LogicError("Unable to use a rule function that takes more than one argument. rule: %r" %self.targets)
    
    @reify
    def _oldest_target(self):
        exists = os.path.exists
        ancient_epoch = 0 #unix time
        return min((get_mtime(target) if exists(target) else ancient_epoch) for target in self.targets )
    
    @reify
    def updated_only(self):
        """makes a list of the reqs which are newer than any of the targets"""
        oldest_target = self._oldest_target
        updated_reqs = [req for req in self.reqs if get_mtime(req) > oldest_target]
        return updated_reqs
        
    def calc_build(self):
        """decides if it needs to be built by recursively asking it's prerequisites
        the same question"""
        
        #No oportunity to optimise calculations to occur only once for rules that are called multiple times
        #unless we change to a shared (global) buildseq + _already_seen set, or pass those structures into
        #the calc_build method call.
        #i.e. if (self in buildseq) or (self in _already_seen): return buildseq
        
        buildseq = OrderedSet()
        
        for req in self.order_only:
            if not os.path.exists(req):
                reqrule = Make.get(req,None) #super(ExplicitRule,self).get(req,None)
                if reqrule:
                    buildseq.add(reqrule.calc_build())
                else:
                    warnings.warn('Make rule for %r has an order_only prerequisite with no rule' %self.targets)
        
        for req in self.reqs:
            reqrule = Make.get(req,None) #super(ExplicitRule,self).get(req,None)
            if reqrule:
                buildseq.add(reqrule.calc_build())
            else: #perform checks
                try:
                    get_mtime(req) #use get_mtime to reduce number of file accesses
                except OSError as e:
                    raise InputError("No rule or file found for %r for targets: %r" %(req,self.targets))
            
        if len(buildseq)==0:
            if self.PHONY or any([not os.path.exists(target) for target in self.targets]):
                buildseq.add(self)
            else:
                oldest_target = self._oldest_target
                
                #Since none of the prerequisites have rules that need to update, we can assume
                #that all prerequisites should be real files (phony rules always update which
                #should skip this section of code). Hence non-existing files imply an malformed build
                #file.
                for req in self.reqs:
                    try: 
                        req_mtime = get_mtime(req)
                        if req_mtime > oldest_target:
                            buildseq.add(self)
                            break
                            
                    except OSError as e: 
                        raise LogicError("A non file prerequisite was found (%r) for targets %r in wrong code path" %(req,self.targets))
        else:
            buildseq.add(self)
        
        return buildseq




class ExplicitTargetRule(ExplicitRule):
    """A multiple target, multiple prerequisite rule where the targets mustn't
    contain wildcards but the reqs list can."""
    
    #rules = {} #shares ExplicitRule's rules datastructure
    
    def __init__(targets,reqs,order_only=None,func=None,PHONY=False):
        """targets - list of targets
        reqs - seq of prerequisites
        order_only - seq of order only prerequisites
        func - a function that should take one or no arguments. Will be
            passed this class instance when run in order to have access
            to its attributes
        """
        self.targets = checkseq(targets)
        self.PHONY = PHONY
        self.allreqs = checkseq(reqs)
        self.reqs = dedup(self.allreqs)
        self.order_only = checkseq(order_only)
        if func: self.func = func
        self.updated_only = self.updated_only()
        
        #Add self to Make registry
        for target in self.targets:
            if target in self.rules:
                warnings.warn('Make takes the last defined rule for each target. Overwriting the rule for %r' %target)
            self.rules[target] = self
    
    def expand_wildcards(self,req):
        """expands any wildcards in the prerequisite. This finds any matches
        for the files in the build directory and for any explicit rules (but
        doesn't search the metarules - impossible to create an explicit 
        prerequisite from a wildcard-wildcard match."""
        ireqs = itertools.chain(*(self.expand_wildcard(req) for req in ireqs))
        iorder_only = itertools.chain(*(self.expand_wildcard(req) for req in iorder_only))

    def expand_wildcard(self,fpath):        
        """Uses the glob module to search the file system and ??an altered glob module??
        to search the meta rules.
        """
        matches = glob.glob(fpath) 
        matches += self.matches(fpath)
        if len(matches) == 0: raise InputError("No matching file or rule found for %r",fpath)
        return dedup(matches)
    
    def matches(self,req):
        """Finds all explicit targets that match the req glob pattern"""
        return ?.filter(req,self.rules.iterkeys())
        




# Meta/Pattern rules
#-------------------------------------------------------------------------------

class MetaRule(Make):
    """The base class for rules that contain wildcards or patterns in their targets
    
    I have resisted the impulse to make MetaRule a descendent of ExplicitRule since it
    performs a different role. MetaRules should never be directly included in the
    build order, instead MetaRules generate Explicit rules (which are then added to the
    build order). 
    """
    # define these in each subclass.
    #meta_rules = {} # compiled regular expression of target: meta_rule
    #_instantiated_rules = {} # cache of instantiated explicit rules
    #_pattern_rankings = {} # registry of the 'lengths' of the wildcard targets.
    
    @class_method
    def get(cls,target,default=None):
        """get the best matched rule for the target from the registry of metarules
        """
        #optimisation
        rule = cls._instantiated_rules.get(target,None)
        if rule: 
            return rule
        #else search metarules
        matches = [self.matchlength(target,pattern) for pattern in cls.meta_rules.keys()]
        matches = [match for match in matches if pattern.match(target)]
        #choose best
        if len(matches) == 1:
            match = matches[0]
        elif len(matches) > 1:
            match = self.best_match(target,matches) # find shortest matching pattern (multiple wildcards?, patterns?)
        else:
            match = None
        #create the desired explicit rule
        if match:
            metarule = cls.meta_rules[match]
            newrule = metarule.individuate(target)
            cls._instantiated_rules[target] = newrule #cache the individuated rule
            return newrule
        else:
            return default
    
    @staticmethod
    def matchlength(target,pattern):
        """looks for a match to the pattern and returns the length of all the groups
        within the pattern - hence it is a requirement that all of the 'wildcard' parts
        of the pattern are within a group for counting purposes"""
        #alternative would be to strip out any special regular expression parts of a pattern
        #to find the explicit parts of each pattern and then find the longest pattern
        res = pattern.match(target)
        if res:
            stemlength = sum(len(group) for group in res.groups())
        else:
            stemlength = maxint
        return stemlength
    
    @staticmethod
    def best_match(target,matches):
        """finds the best matched pattern for the target.
        This assumes that each match regular expression does find a match with the target.
        It also assumes that each wildcard etc in the re pattern is surrounded by parenthesees.
        """
        i = argmin(sum(len(group) for group in pattern.match(target).groups()) for pattern in matches)
        return matches[i]
    
    def __init__(self,targets,reqs,order_only=None,func=None,PHONY=False):
        """targets - list of targets
        reqs - seq of prerequisites
        order_only - seq of order only prerequisites
        func - a function that should take one or no arguments. Will be
            passed this class instance when run in order to have access
            to its attributes.
        """
        self.targets = checkseq(targets)
        self.PHONY = PHONY
        self.allreqs = checkseq(reqs)
        self.order_only = checkseq(order_only)
        
        #self.re_targets = [] #must be defined in the child classes.
        
    def individuate(self,target):
        """updates the explicit rule for the target. Will raise InputError
        if the target is incompatible with the metarule."""
        raise NotImplementedError
        
    def ismatch(self,target):
        """decides if the target is a match for this metarule."""
        for pattern in self.re_targets:
            if pattern.match(target):
                return True        
        return False


## rules where those with multiple targets are still only run once.
##------------------------------------------------------------------------------


class WildSharedRule(MetaRule):
    """A multiple target, multiple prerequisite rule where the targets and the
    reqs can both contain wildcards. The rule will only run once no matter how
    many different targets ask for it to run. The targets attribute will be 
    updated to contain each target that requests it.
    """
    meta_rules = {} # compiled regular expression of target: meta_rule
    _instantiated_rules = {} # cache of instantiated explicit rules
    _pattern_rankings = {} # registry of the 'lengths' of the wildcard targets.
        
    def __init__(self,targets,reqs,order_only=None,func=None,PHONY=False):
        """targets - list of targets
        reqs - seq of prerequisites
        order_only - seq of order only prerequisites
        func - a function that should take one or no arguments. Will be
            passed this class instance when run in order to have access
            to its attributes
        """
        super(WildSharedRule,self).__init__(targets,reqs,order_only=None,func=None,PHONY=False)
        #check parameters
        
        
        # Some of the targets may be explicit, in which case we can create the explicitRule now
        explicit_targets = [target for target in targets if not fpmatch.has_magic(target)]
        self.explicitrule = ExplicitTargetRule(targets=explicit_targets,
                                        reqs=ireqs,order_only=iorder_only,
                                        func=self.func,PHONY=self.PHONY)
        
        #Add self to registry of rules
        wild_targest = [target for target in targets if fpmatch.has_magic(target)]
        self.re_targets = [fpmatch.precompile(pattern) for pattern in wild_targets]
        for regex in self.re_targets:
            self.meta_rules[regex] = self
        
        #calculate pattern lengths
        rankings = [len(fpmatch.strip_specials(pattern)) for pattern in wild_targets]
        for regex,rank in zip(self.re_targets,rankings):
            self._pattern_rankings[regex] = rank
        
    def individuate(self,target):
        """updates the explicit rule for the target. Will raise InputError
        if the target is incompatible with the metarule"""
        #check target parameter
        
        
        #Adding new target to explicit rule's target attribute.
        erule = self.explicitrule
        erule.targets = dedup(erule.targets + [target])
        
        #Nb. We don't add target to the ExplicitRule rule registry since that would make
        # the build calculation order dependent/non-deterministic. Instead we add the
        # rule to a class attribute dict (this is done by get() class method).
        
        #Last problem, old version of rule may already be in the build orderedset and I've just mutated the object?
        # python uses the id() of an object for its hash if no __hash__ method is defined, therefore the object can
        # be mutated without issue. 
        return erule




## rules for which those with multiple targets are shorthand for multiple individual rules.
##-----------------------------------------------------------------------------------------

class WildRule(MetaRule):
    """A meta rule that can specialise to an explicit rule. It takes wildcards and
    in the target and req lists. Multiple targets lead to individualised explicit 
    rules."""
    meta_rules = {} # compiled regular expression of target: meta_rule
    _instantiated_rules = {} # cache of instantiated explicit rules
    _pattern_rankings = {} # registry of the 'lengths' of the wildcard targets.
        
    def __init__(self,targets,reqs,order_only=None,func=None,PHONY=False):
        """targets - list of targets
        reqs - seq of prerequisites
        order_only - seq of order only prerequisites
        func - a function that should take one or no arguments. Will be
            passed this class instance when run in order to have access
            to its attributes.
        """
        super(WildRule,self).__init__(targets,reqs,order_only=None,func=None,PHONY=False)
        #Check parameters
        
        
        #Some of the targets may be explicit, in which case we can just directly create ExplicitRules
        explicit_targets = [target for target in targets if not fpmatch.has_magic(target)]
        for target in explicit_targets:
            ExplicitTargetRule(targets=target,reqs=ireqs,order_only=iorder_only,
                                func=self.func,PHONY=self.PHONY)
        
        #Add self to registry of rules
        wild_targest = [target for target in targets if fpmatch.has_magic(target)]
        self.re_targets = [fpmatch.precompile(pattern) for pattern in wild_targets]
        for regex in self.re_targets:
            self.meta_rules[regex] = self
        
        #calculate pattern lengths
        rankings = [len(fpmatch.strip_specials(pattern)) for pattern in wild_targets]
        for regex,rank in zip(self.re_targets,rankings):
            self._pattern_rankings[regex] = rank
        
    def individuate(self,target):
        """creates an explicit rule for the target. Will raise InputError
        if the target is incompatible with the metarule"""
        #check target
        
        #expanding wildcards in reqs        
        newrule = ExplicitTargetRule(targets=target,reqs=ireqs,order_only=iorder_only,
                                func=self.func,PHONY=self.PHONY)
        return newrule

        



class PatternRule(MetaRule):
    """A meta rule that can specialise to an explicit rule. It takes wildcards and
    patterns in the target and req lists. Multiple targets lead to individualised
    explicit rules.
    """
    meta_rules = {}
    _instantiated_rules = {} # cache of instantiated explicit rules
    _pattern_rankings = {} # registry of the 'lengths' of the wildcard targets.
    
    def __init__(self,targets,reqs,order_only=None,func=None,PHONY=False):
        """Note: All targets must have at least the same number of % wildcards as the prerequisite
        with the highest number of them."""
        super(PatternRule,self).__init__(targets,reqs,order_only=None,func=None,PHONY=False)
        #Check parameters
        
        #Create registry
        self.re_targets = [fpmatch.precompile(pattern) for pattern in targets]
        for regex in self.re_targets:
            self.meta_rules[regex] = self
        
        #calculate pattern lengths
        rankings = [len(fpmatch.strip_specials(pattern)) for pattern in targets]
        for regex,rank in zip(self.re_targets,rankings):
            self._pattern_rankings[regex] = rank
        
    
    def individuate(self,target):
        """creates an explicit rule for the target. Will raise InputError
        if the target is incompatible with the metarule"""
        #check target
        
        #pattern matching, finding best match
        pattern = ?
        ireqs = [req.replace('%',pattern) for req in self.allreqs]
        iorder_only = [req.replace('%',pattern) for req in self.order_only] 
        newrule = ExplicitTargetRule(targets=target,reqs=ireqs,order_only=iorder_only,
                                func=self.func,PHONY=self.PHONY)
        newrule.pattern = pattern #useful attribute
        return newrule





"""
Questions:
Is a singleton class like Build a good idea?
Should MetaRule and ExplicitRule be usable directly? In which case, should they add themselves to the build class
Does expand_wildcards belong on MetaRule? This means that it needs to be able call the Build.get() method, but
individualate needs to call expand_wildcards() whatever and so it must know how to access the build class anyway.
If MetaRule and ExplicitRule were never called directly, Build could be a normal class and could pass itself to
their initialisation routines. Then could have multiple copies of Build (but why?)

Should I have a separate decorate function/class or should I add it to one of the classes? or both of the classes