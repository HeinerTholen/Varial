import copy
import inspect
import math
from ROOT import TH1D


def list2histogram(values, name="histo", title=None, n_bins=0):
    """Makes histogram from list of values."""
    mi, ma, n = min(values), max(values), len(values)
    val_range = ma - mi
    bounds = mi - 0.1*val_range, ma + 0.1*val_range
    if n_bins:
        n_bins = int(n_bins)
    else:
        n_bins = list2nbins_scott(values)

    if not title:
        title = name
    histo = TH1D(name, title, n_bins, *bounds)
    for v in values:
        histo.Fill(v)
    return histo


def list2nbins_scott(values):
    """
    Taken from equation (3) in
    http://arxiv.org/abs/physics/0605197
    """
    mi, ma, n = min(values), max(values), len(values)
    val_range = ma - mi
    mean = sum(values) / n
    var = sum((v-mean)**2 for v in values) / n
    return int(math.ceil(val_range * n**.333 / 3.49 / var))


def deepish_copy(obj):
    if (
        isinstance(obj, type)
        or callable(obj)
        or inspect.ismodule(obj)
        or inspect.isclass(obj)
        #or str(type(obj)) == "<type 'generator'>"
    ):
        return obj
    if type(obj) == list:
        return list(deepish_copy(o) for o in obj)
    if type(obj) == tuple:
        return tuple(deepish_copy(o) for o in obj)
    if type(obj) == dict:
        return dict((k, deepish_copy(v)) for k, v in obj.iteritems())
    if type(obj) == set:
        return set(deepish_copy(o) for o in obj)
    if hasattr(obj, "__dict__"):
        cp = copy.copy(obj)
        cp.__dict__.clear()
        for k, v in obj.__dict__.iteritems():
            cp.__dict__[k] = deepish_copy(v)
        return cp
    return obj


############################################################ ResettableType ###
_instance_init_states = {}


def _wrap_init(original__init__):
    def init_hook(inst, *args, **kws):
        if inst not in _instance_init_states:
            _instance_init_states[inst] = None
            res = original__init__(inst, *args, **kws)
            _instance_init_states[inst] = deepish_copy(inst.__dict__)
            return res
        else:
            return original__init__(inst, *args, **kws)
    return init_hook


def _reset(inst):
    inst.__dict__.clear()
    inst.__dict__.update(
        deepish_copy(_instance_init_states[inst])
    )


def _update_init_state(inst):
    _instance_init_states[inst] = deepish_copy(inst.__dict__)


class ResettableType(type):
    """
    Wraps __init__ to store object _after_ init.

    >>> class Foo(object):
    ...     __metaclass__ = ResettableType
    ...     def __init__(self):
    ...         self.bar = 'A'
    >>> foo = Foo()
    >>> foo.bar = 'B'
    >>> foo.reset()
    >>> foo.bar
    'A'
    """
    def __new__(mcs, *more):
        mcs = super(ResettableType, mcs).__new__(mcs, *more)
        mcs.__init__ = _wrap_init(mcs.__init__)
        mcs.reset = _reset
        mcs.update = _update_init_state
        return mcs


################################################################# decorator ###
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
    def __init__(self, target=None, deep_decoration=True, **kws):
        """
        Init a decorator. "deep_decoration" activates a wrapping of the
        original methods. If true, direct calls to the inner object methods
        will go through all decorators. This is especially sensible, when the
        inner object calls methods of its own.
        """
        if not self.__dict__.has_key('dec_par'):
            self.__dict__['dec_par'] = dict()
        self.__dict__['dec_par'].update(kws)
        if not target:
            return
        self.__dict__['decoratee']  = target

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

    def __call__(self, target, dd=True):
        Decorator.__init__(self, target, dd)
        return self

    def get_decorator(self, klass):
        """
        Runs over all inner decorators, returns the match.

        If klass is str, then __class__.__name__ must be equal.
        If klass is a class object, then all subclasses are returned as well.
        """
        inner = self
        if type(klass) == str:
            while isinstance(inner, Decorator):
                if inner.__class__.__name__ == klass:
                    return inner
                inner = inner.decoratee
        elif type(klass) == type:
            while isinstance(inner, Decorator):
                if isinstance(inner, klass):
                    return inner
                inner = inner.decoratee

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
