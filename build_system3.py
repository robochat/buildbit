#!/usr/bin/env python2
"""a simple build system inspired by gnu make"""

from orderedset import OrderedSet
#import pathlib
import os.path
import warnings
import glob
import itertools
import inspect
import functools
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

def memoize(obj):
    cache = obj.cache = {}
    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]
    return memoizer


class reify(object):
    """ Use as a class method decorator.  It operates almost exactly like the
    Python ``@property`` decorator, but it puts the result of the method it
    decorates into the instance dict after the first call, effectively
    replacing the function it decorates with an instance variable.  It is, in
    Python parlance, a non-data descriptor.  An example:
    .. code-block:: python
       class Foo(object):
           @reify
           def jammy(self):
               print('jammy called')
               return 1
    And usage of Foo:
    >>> f = Foo()
    >>> v = f.jammy
    'jammy called'
    >>> print(v)
    1
    >>> f.jammy
    1
    >>> # jammy func not called the second time; it replaced itself with 1
    """
    def __init__(self, wrapped):
        self.wrapped = wrapped
        functools.update_wrapper(self, wrapped)

    def __get__(self, inst, objtype=None):
        if inst is None:
            return self
        val = self.wrapped(inst)
        setattr(inst, self.wrapped.__name__, val)
        return val

@memoize
def get_mtime(fpath):
    return os.path.getmtime(fpath)
    
class Make(object):
    """Acts as a base class and contains the get() method for finding the best match
    for a target/req from the child classes."""
    searchorder = [] #[ExplicitRule,WildSharedRule,WildRule,PatternRule] #custom child classes should add themselves to this list
                
    @classmethod
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
                
    @classmethod
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
    
    @classmethod
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
        #self.updated_only = self.updated_only()
        
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
    
    #@reify
    @memoize
    def _oldest_target(self):
        exists = os.path.exists
        ancient_epoch = 0 #unix time
        return min((get_mtime(target) if exists(target) else ancient_epoch) for target in self.targets )
    
    #@reify
    @memoize
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
        self._allreqs = checkseq(reqs)
        self._order_only = checkseq(order_only)
        if func: self.func = func
        #self.updated_only = self.updated_only()
        
        #Add self to Make registry
        for target in self.targets:
            if target in self.rules:
                warnings.warn('Make takes the last defined rule for each target. Overwriting the rule for %r' %target)
            self.rules[target] = self
    
    #delay expansion because we can only do it after all of the build rules have been defined
    
    #@reify
    @memoize
    def allreqs(self):
        return itertools.chain(*(self.expand_wildcard(req) for req in self._allreqs))
    
    #@reify
    @memoize
    def reqs(self):
        return dedup(self.allreqs)
    
    #@reify
    @memoize
    def order_only(self):
        return itertools.chain(*(self.expand_wildcard(req) for req in self._order_only))
    
    def expand_wildcard(self,fpath):        
        """Uses the glob module to search the file system and ??an altered glob module??
        to search the meta rules.
        """
        matches = glob.glob(fpath) 
        matches += fpmatch.filter(req,self.rules.iterkeys())
        if len(matches) == 0: raise InputError("No matching file or rule found for %r",fpath)
        return dedup(matches)




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
    
    @classmethod
    def get(cls,target,default=None):
        """get the best matched rule for the target from the registry of metarules
        """
        #optimisation
        rule = cls._instantiated_rules.get(target,None)
        if rule: 
            return rule
        #else search metarules
        matches = [regex for regex in cls.meta_rules.keys() if regex.match(target)]
        #choose best
        if len(matches) == 1:
            match = matches[0]
        elif len(matches) > 1:
            # find longest matching pattern (explicit part only) using _pattern_rankings dict
            i = argmax(self._pattern_rankings[regex] for regex in matches)
            match = matches[i]
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
        
        self.explicit_rules = [] # definition necessary here for func descripter to work.
        self._func = func
        
        #Add self to registry of rules
        wild_targets = [target for target in targets if fpmatch.has_magic(target)]
        self.re_targets = [fpmatch.precompile(pattern) for pattern in wild_targets]
        for regex in self.re_targets:
            self.meta_rules[regex] = self
        
        #calculate pattern lengths
        rankings = [len(fpmatch.strip_specials(pattern)) for pattern in wild_targets]
        for regex,rank in zip(self.re_targets,rankings):
            self._pattern_rankings[regex] = rank
        
        
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
    
    @property
    def func(self):
        return self._func

    #this allows us to have late binding of the build function to the rule instance
    @func.setter
    def func(self,newfunc):
        self._func = newfunc
        for explicit_rule in self.explicit_rules:
            explicit_rule.func = newfunc


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
        
        
        # A single ExplicitRule will shared between all targets.
        explicit_targets = [target for target in targets if not fpmatch.has_magic(target)]
        self.explicitrules = [ExplicitTargetRule(targets=explicit_targets,
                                        reqs=ireqs,order_only=iorder_only,
                                        func=self.func,PHONY=self.PHONY)]
        #only one rule is defined but we store it in the explicitrules list for
        #compatibility with the parent object's func getter/setter descriptors.
        

        
    def individuate(self,target,regex):
        """updates the explicit rule for the target. Will raise InputError
        if the target is incompatible with the metarule"""
        #check target parameter
        
        
        #Adding new target to explicit rule's target attribute.
        erule = self.explicitrule[0]
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
        #saving references to explicit rules to allow us to have late-binding of the build func
        self.explicit_rules = [
            ExplicitTargetRule(targets=target,reqs=ireqs,order_only=iorder_only,func=self.func,PHONY=self.PHONY)
            for target in explicit_targets]


        
    def individuate(self,target,regex):
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
        

        
    
    def individuate(self,target,regex):
        """creates an explicit rule for the target. Will raise InputError
        if the target is incompatible with the metarule"""
        #check target
        
        #inplace pattern substitution
        def subst_patterns(s,patterns):
            for pattern in patterns:
                s=s.replace('%',pattern,1)
            return s
        #pattern matching, finding best match
        res =regex.match(target)
        if not res: raise LogicError
        patterns = res.groups()
        ireqs = [subst_patterns(req,patterns) for req in self.allreqs]
        iorder_only = [subst_patterns(req,patterns) for req in self.order_only]
        newrule = ExplicitTargetRule(targets=target,reqs=ireqs,order_only=iorder_only,
                                func=self.func,PHONY=self.PHONY)
        newrule.pattern = pattern #useful attribute
        return newrule




## Adding children classes to Make searchlist

Make.searchorder = [ExplicitRule,WildSharedRule,WildRule,PatternRule]


## build system function decorator (user interface)
##-----------------------------------------------------------------------------------------

def rule(targets,reqs,order_only=None,func=None,PHONY=False,shared=False):
    """selects the appropriate rule class to use and returns a decorator
    function if func==None. 
        targets - single target or sequence of targets
        reqs - single prerequisite or sequence of prerequisites
        order_only - single dependency or sequence of order only prerequisites
        func - the build function that should take one or no arguments. Will be
            passed this class instance when run in order to have access
            to its attributes.
        PHONY - a phony rule always runs irrespective of file modification times
        shared - shared rules run their build function a single time for all of
            their targets.
    targets and reqs may contain glob patterns (see fnmatch and glob modules).
    They may also contain the '%' wildcard for defining pattern rules (like
    make).
    """
    if shared:
        if not any(fpmatch.has_magic(target) for target in targets):
            if not any(fpmatch.has_magic(req) for req in itertools.chain(reqs,order_only)):
                newrule = ExplicitRule(targets,reqs,order_only,func,PHONY)
            else:
                newrule = ExplicitTargetRule(targets,reqs,order_only,func,PHONY)
        elif has_pattern(targets):
            raise InputError('shared pattern rule type not written yet')
        else: #wildcard targets
            newrule = WildSharedRule(targets,reqs,order_only,func,PHONY)
    else:
        if not any(fpmatch.has_magic(target) for target in targets):
            if not any(fpmatch.has_magic(req) for req in itertools.chain(reqs,order_only)):
                newrules = [ExplicitRule(target,reqs,order_only,func,PHONY) for target in targets] 
                #or maybe use WildRule??
            else:
                newrules = [ExplicitTargetRule(target,reqs,order_only,func,PHONY) for target in targets] 
                #or maybe use WildRule??
        elif any(fpmatch.has_pattern(target) for target in targets): 
            #in fact all targets should have a pattern wildcard but error checking will occur in class.
            newrule = PatternRule(target,reqs,order_only,func,PHONY)
        else: #wildcard targets
            newrule = WildRule(targets,reqs,order_only,func,PHONY)
    
    #-------------------
    if func==None:
        if newrules:
            def setfunc(func):
                for newrule in newrules:
                    newrule.func = func
                return func #so that we can have multiple decorators on each function!
        else:
            def setfunc(func):
                newrule.func = func
                return func #so that we can have multiple decorators on each function!

        return setfunc


## test stuff
##-----------------------------------------------------------------------------------------


def reset_cache():
    """resets the memoize caches"""
    for obj in [get_mtime,ExplicitRule._oldest_target, ExplicitRule.updated_only,
                ExplicitTargetRule.allreqs, ExplicitTargetRule.reqs, ExplicitTargetRule.order_only]:
        if hasattr(obj,'cache'):
            obj.cache = {}

"""
Questions:
Is a singleton class like Build a good idea?
Should MetaRule and ExplicitRule be usable directly? In which case, should they add themselves to the build class
Does expand_wildcards belong on MetaRule? This means that it needs to be able call the Build.get() method, but
individualate needs to call expand_wildcards() whatever and so it must know how to access the build class anyway.
If MetaRule and ExplicitRule were never called directly, Build could be a normal class and could pass itself to
their initialisation routines. Then could have multiple copies of Build (but why?)

Should I have a separate decorate function/class or should I add it to one of the classes? or both of the classes
"""
