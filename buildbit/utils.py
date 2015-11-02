from collections import Iterable
from types import StringTypes
import functools

def checksingleinput(val):
    """checks that input is not a sequence"""
    if isinstance(val,StringTypes): pass
    elif isinstance(val,Iterable): raise AssertionError("input should not be a sequence: %r" %val)
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


## Decorators ########################

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


class cached_property(object):
    """lazy descriptor

    Used as a decorator to create lazy attributes. Lazy attributes
    are evaluated on first use.
    """
    class Null(object): pass # None might be a valid return value from method so using custom object

    def __init__(self, func):
        self._func = func
        functools.wraps(self._func)(self)
        self.cache = {} #In a long running process this could cause a memory leak though.
        # Better to use a weakref dictionary?

    def __call__(self,func):
        self._func = func
        return self

    def __get__(self,obj,cls):
        if obj is None:
            return self
        val = self.cache.get(obj,self.Null)
        if val == self.Null:
            val = self.cache[obj] = self._func(obj)
        return val

    def reset_cache(self):
        """Reset the cache.
        """
        self.cache = {}