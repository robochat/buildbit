import re
import os.path
import imp

def translate(pat):
    """Translate a shell PATTERN to a regular expression.

    There is no way to quote meta-characters.
    """
    i, n = 0, len(pat)
    res = ''
    wildcard = '[^/]*' if os.path.sep is '/' else '[^/'+re.escape(os.path.sep)+']*'
    while i < n:
        c = pat[i]
        i = i+1
        if c == '*':
            res = res + wildcard
        elif c == '?':
            res = res + wildcard
        elif c == '%':
            res = res + '('+wildcard+')'
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j = j+1
            if j < n and pat[j] == ']':
                j = j+1
            while j < n and pat[j] != ']':
                j = j+1
            if j >= n:
                res = res + '\\['
            else:
                stuff = pat[i:j].replace('\\','\\\\')
                i = j+1
                if stuff[0] == '!':
                    stuff = '^' + stuff[1:]
                elif stuff[0] == '^':
                    stuff = '\\' + stuff
                res = '%s[%s]' % (res, stuff)
        else:
            res = res + re.escape(c)
    return res + '\Z(?ms)'


# Bring in fnmatches other functions
_fpmatch = imp.load_module('_fpmatch', *imp.find_module('fnmatch'))
_fpmatch.translate = translate #monkey patch!
from _fpmatch import *



def precompile(pat):
    """pre-compile the glob pattern into a compiled regular expression"""
    regex = translate(os.path.normcase(pat))
    return re.compile(regex)

def strip_specials(pat):
    """Strip all the special characters from a pattern. This will be used to 
    find the best match when there are multiple matching patterns.
    """
    i, n = 0, len(pat)
    res = ''
    while i < n:
        c = pat[i]
        i = i+1
        if c == '*':
            pass
        elif c == '?':
            pass
        elif c == '%':
            pass
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j = j+1
            if j < n and pat[j] == ']': #weird corner case [] treated as a literal, not dropped.
                j = j+1
            while j < n and pat[j] != ']':
                j = j+1
            if j >= n:
                res = res + '['
            else:
                i = j+1
        else:
            res += c
    return res


magic_check = re.compile('[*?%[]')

def has_magic(s):
    return magic_check.search(s) is not None

def has_pattern(s):
    """find if glob  has a rule pattern (%) wildcard.
    """
    i, n = 0, len(s)
    res = False
    while i < n:
        c = s[i]
        i = i+1
        if c == '%':
            res = True
        elif c == '[':
            j = i
            while j < n and s[j] != ']':
                j = j+1
            if j >= n:
                pass #bracket never closed so treating [ as a literal
            else:
                i = j+1
    return res
