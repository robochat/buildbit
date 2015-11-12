from setuptools import setup

setup(name='buildbit',
        version='0.4.0',
        description='Yet another build system inspired by make and python decorators',
        classifiers=[
          "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
          "Environment :: Console",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.6",
          "Programming Language :: Python :: 2.7",
          "Development Status :: 3 - Alpha",
          "Intended Audience :: Developers",
          "Natural Language :: English",
          "Operating System :: OS Independent",
          "Topic :: Software Development :: Build Tools"
           ],
        author='robochat',
        author_email='rjsteed@talk21.com',
        url='https://github.com/robochat/buildbit',
        license='GPLv3',
        keywords='make build',
        #packages=[],
        #package_data={'?'  :['']},
        #py_modules=[''],
        #scripts=[],
        #data_files=[('',[,'README.md'])],
        install_requires=['orderedset','unittest2'],
        #zip_safe=False,
        long_description="""\
This is a build system for compiling programs or performing tasks involving many files.
Most importantly it tries to do rebuilds efficiently by only rerunning those tasks for
which prerequisite files have changed. It is heavily heavily inspired by GNU make but
instead of being a DSL around shell script snipnets, it is used from within a python 
script and so has all of the features of python available for use.

The main interface is an object factory called Rule, that defines the dependency graph. ::

    Rule(targets=[],reqs=[],order_only=[],func=None,PHONY=False,shared=False)

The recipe functions can be supplied as an argument or assigned to the 'func' attribute
of the returned object or Rule can be used as a function decorator. The recipe functions
is either a python function or a command line string. The command lines string/sequence of
strings (see subprocess module) can contain various space separated list of paths using
the following parameters: 

    * targets, $@
    * allreqs, $+
    * reqs, $^
    * order_only, $|
    * updated_only, $?

which we can include using python format specification i.e. ``ls {reqs} > {targets[0]}``.
Alternatively, we can access the rule instance directly using 
``ls {self.reqs} > {self.targets[0]}``. Similarly, the build functions can optionally take
a single parameter which will be passed the rule instance so that they can access the
rule attributes in a similar manner i.e. ::

    def changed(self):
        print self.updated_only

(I tend to use self as the parameter name even though the functions are not bound methods
of the rule instances).

The targets, reqs and order_only parameters of Rule will accept sequences or simple strings
of file paths. These can also contain wildcards conforming to the format used by the 
python standard libraries fnmatch or glob where metacharacters are ``[][!]*?``. In addition
the wildcard character '``%``' can be used as in gmake to create pattern rules.       

Here is a small example of usage::

    from bob import Rule as rule
    from sh import touch

    rule('tests',None,func=['mkdir','{targets}'])

    r1 = rule('tests/test1.txt',None,order_only='tests')
    r2 = rule('tests/test2.txt',None)
    r3 = rule('tests/test3.txt',None)

    @rule(['tests/foo.txt','tests/foo2.txt'],'tests/test*.txt',shared=True)
    @rule('tests/ex%.txt','tests/test%.txt')
    def mytouch(self):
        touch(self.targets)

    for r in r1,r2,r3:
        r.func = mytouch

    rule('All',['tests','tests/foo2.txt','tests/ex2.txt'],PHONY=True)

    if __name__=="__main__":
        rule.main() #supplies a simple commandline interface

    # Can alternatively easily run buildbit from within script. 
    if False: #__name__=="__main__":
        buildseq = rule.calc_build('All')
        print buildseq
        response=raw_input("run build? [(y)es/(n)o]")
        if response in ('y','yes'):
            rule.build(buildseq)

There are some differences from GNU make. In buildbit, we can explicitly decide whether
we want rules to be shared between targets or not in order to have more efficient builds.
Wildcard prerequisites will search the rules with explicitly defined targets for any
matches as well as the filesystem. Also, pattern rules are not currently shared across
their targets unlike in gmake.


To Do
~~~~~

Add class for shared pattern rules
write unit tests
create dependency graphs (using graphviz)   
        """,
        )


