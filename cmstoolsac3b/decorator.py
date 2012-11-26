from new import function, instancemethod
from inspect import getmembers, ismethod
from functools import wraps

def _decorator_sensitive(f):
    """
    Wrapper for inner object methods. Forwards calls to the outer decorator.
    """
    @wraps(f)
    def dec_sens(self, *args, **kws):
        return f(self._outermost_decorator, *args, **kws)
    return dec_sens

class Decorator(object):
    """
    Implements the decorator pattern. For a basic outline, have a look at
    http://en.wikipedia.org/wiki/Decorator_pattern
    However, in python, no subclassing and no getters/setters are needed,
    thanks to __getattr__ and __setattr__.

    >>> class Foo(object):
    ...     def f1(self):
    ...         print "in Foo.f1()"
    ...     def f2(self):
    ...         print "in Foo.f2()"
    >>> class FooDecorator(Decorator):
    ...     def f2(self):
    ...         print "in FooDecorator.f2()"
    ...         self.decoratee.f2() # VERY IMPORTANT !! pass on the call...
    >>> x = Foo()
    >>> y = FooDecorator(x)
    >>> y.f1()
    in Foo.f1()
    >>> y.f2()
    in FooDecorator.f2()
    in Foo.f2()
    """
    def __init__(self, target, deep_decoration = True):
        """
        Init a decorator. "deep_decoration" activates a wrapping of the
        original methods. If true, direct calls to the inner object methods
        will go through all decorators. This is especially sensible, when the
        inner object calls methods of its own.
        """
        # the only datamember of a decorator
        self.__dict__['decoratee']  = target
        self.__dict__['dec_par'] = dict()

        # this is automatically forwarded to the inner decoratee
        target._outermost_decorator = self

        if deep_decoration and not isinstance(target, Decorator):
            # make the inner object decorator-aware
            # the mechanism is the same as if @decorator_sensitive would be
            # applied to each of the inner objects methods.

            # in some cases needed
            target._inner_decoratee = target

            # get methods
            members = getmembers(target)
            methods = [m for m in members if ismethod(m[1])]
            for m in methods:

                # wrap methods properly with decorator_sensitive(...)
                m_func = function(m[1].func_code, m[1].func_globals)
                m_func = _decorator_sensitive(m_func)
                m_func = instancemethod(m_func, target)

                # do the monkey-'wrap'
                setattr(target, m[0], m_func)

    def __getattr__(self, name):
        return getattr(self.decoratee, name)

    def __setattr__(self, name, value):
        setattr(self.decoratee, name, value)

    def get_decorator(self, name):
        """
        Runs over all inner decorators, returns the one according to 'name'.
        """
        inner = self
        while isinstance(inner, Decorator):
            inner = inner.decoratee
            if inner.__class__.__name__ == name:
                return inner

    def insert_decorator(self, new_dec):
        """
        Inserts decorator right after me.
        """
        assert issubclass(new_dec, Decorator)
        self.__dict__["decoratee"] = new_dec(self.decoratee)
        return self.decoratee

    def replace_decorator(self, old, new_dec):
        """
        Changes old for new in the chain of decorators.
        """
        assert issubclass(new_dec, Decorator)
        inner = self.decoratee
        outer = self
        while isinstance(inner, Decorator):
            if inner.__class__.__name__ == old:
                outer.__dict__['decoratee'] = new_dec(inner.decoratee, False)
                break
            outer = inner
            inner = outer.decoratee

    def remove_decorator(self, old):
        """
        Searches 'old' and removes it.
        """
        inner = self.decoratee
        outer = self
        while isinstance(inner, Decorator):
            if inner.__class__.__name__ == old:
                outer.__dict__['decoratee'] = inner.decoratee
                break
            outer = inner
            inner = outer.decoratee

    def print_decorators(self):
        """
        For debugging.
        """
        decs  = ""
        inner = self
        while isinstance(inner, Decorator):
            decs += inner.__class__.__name__ + "\n"
            inner = inner.decoratee
        self.message.emit(
            self,
            "DEBUG _______________(inner)_decorator_chain_______________"
            + "\n"
            + decs
        )


if __name__ == "__main__":
    import doctest
    doctest.testmod()
