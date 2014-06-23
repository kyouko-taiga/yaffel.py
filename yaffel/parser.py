# This source file is part of yaffel-py
# Main Developer : Dimitri Racordon (kyouko.taiga@gmail.com)
#
# Copyright 2014 Dimitri Racordon
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import namedtuple
from funcparserlib.lexer import make_tokenizer, Token, LexerError
from funcparserlib.parser import some, a, many, maybe, finished, skip, with_forward_decls
from functools import reduce

from yaffel.types import *

import operator, sys

keywords = ['for', 'in', 'not in']

def tokenize(s):
    regexps = {
        'escaped':   r'\\(?P<standard>["\\/bfnrt])',
        'unescaped': r'[^"\\]' }
    grammar_specifications = [
        ('space',    (r'[ \t\r\n]+',)),
        ('number',   (r'-?(0|([1-9][0-9]*))(\.[0-9]+)?([Ee][+-][0-9]+)?',)),
        ('string',   (r'"[^"]*"',)),                                # unsupported escaped quotes
        ('operator', (r'(\*\*)|(and)|(or)|(in)|[{}\[\]\(\)\-\+\*/=><\.,:]',)),
        ('name',     (r'[A-Za-z_][A-Za-z_0-9]*',)),
    ]

    t = make_tokenizer(grammar_specifications)
    return [x for x in t(s) if x.type not in ['space']]

def parse(seq):
    # auxiliary helper functions
    const       = lambda x: lambda _: x
    uncurry     = lambda f: lambda x: f(*x)
    token_value = lambda t: t.value
    token_type  = lambda t: some(lambda x: x.type == t)

    # semantic actions
    def make_number(t):
        try:
            return int(t)
        except ValueError:
            return float(t)

    def eval_cst_expr(head, tail):
        return reduce(lambda s, p: p[0](s, p[1]), tail, head)

    def eval_expr(x):
        if hasattr(x[0], '__call__'):
            # Whenever an expression is parsed, an instance of Expression is
            # created. Then, when we want to evaluate the result of the
            # expression for a given binding, this function will be called,
            # using the context bindings as the function parameters.
            context = x[1] or {}
            return x[0](**context)

        # If the expression is constant, we don't need to evaluate it.
        return x[0]

    def make_expression(head, tail):
        # try to evaluate as a constant expression, if possible
        # terms = [head] + [t for _,t in tail]
        # if not any(isinstance(t, Token) or hasattr(t, '__call__') for t in terms):
        #     return eval_cst_expr(head, tail)

        # don't create an additional function if 'head' is the only term and is already callable
        if not tail and hasattr(head, '__call__'):
            return head

        # return a function that will take unbound variables as parameters
        return Expression(head, tail)

    def make_binding(t):
        return (token_value(t[0]), t[1])

    def make_context(head, tail):
        context = {head[0]: head[1]}
        for k,v in tail:
            if k in context: raise EvaluationError("'%s' is already bound" % k)
            context[k] = v
        return context

    def make_enum(x):
        # check that the enumeration is not the empty set
        if x is not None:
            e = {x[0]} | {e for e in x[1]}
            return Enumeration(*e)

        # return the empty set
        return Enumeration()

    def make_range(x):
        return Range(x[0],x[1])

    def make_set(x):
        return Set(*x)

    def make_tuple(x):
        if x is not None:
            return tuple([x[0]] + [e for e in x[1]])
        return tuple()

    def make_application(x):
        return Application(x[0], x[1])

    def make_function(x):
        args = [token_value(t) for t in [x[0]] + [a for a in x[1]]]
        expr = x[2]
        return AnonymousFunction(args, expr)

    # primitives
    op          = lambda s: a(Token('operator', s))
    op_         = lambda s: skip(op(s))

    kw          = lambda s: a(Token('name', s))
    kw_         = lambda s: skip(kw(s))

    add         = op('+') >> const(operator.add)
    sub         = op('-') >> const(operator.sub)
    mul         = op('*') >> const(operator.mul)
    div         = op('/') >> const(operator.truediv)
    power       = op('**') >> const(operator.pow)
    and_        = op('and') >> const(operator.and_)
    or_         = op('or') >> const(operator.or_)

    name        = token_type('name')
    number      = token_type('number') >> token_value >> make_number
    string      = token_type('string') >> token_value

    # grammar rules
    mul_op      = mul | div
    add_op      = add | sub
    bin_op      = or_ | and_

    atom        = with_forward_decls(lambda:
                    fx_app | number | name | set_expr | (op_('(') + expr + op_(')')))
    factor      = atom + many(power + atom) >> uncurry(make_expression)
    term        = factor + many(mul_op + factor) >> uncurry(make_expression)
    expr        = term + many((add_op | bin_op) + term) >> uncurry(make_expression)

    fx_anon     = kw_('f') + maybe(name + many(op_(',') + name)) + op_(':') + expr >> make_function

    binding     = with_forward_decls(lambda: name + op_('=') + evaluation >> (make_binding))
    context     = binding + many(op_(',') + binding) >> uncurry(make_context)

    evaluable   = expr + maybe(kw_('for') + context) >> eval_expr
    evaluation  = (fx_anon | evaluable) | (op_('(') + (fx_anon | evaluable) + op_(')'))

    enumeration = op_('{') + maybe(expr + many(op_(',') + expr)) + op_('}') >> make_enum
    range_      = op_('{') + expr + op_(':') + expr  + op_('}') >> make_range
    set_        = with_forward_decls(lambda:
                    op_('{') + expr + maybe(kw_('for') + set_context) + op_('}') >> make_set)
    set_expr    = (enumeration | range_ | set_)

    set_binding = name + op_('in') + set_expr >> make_binding
    set_context = set_binding + many(op_(',') + set_binding) >> uncurry(make_context)

    tuple_      = op_('(') + maybe(expr + many(op_(',') + expr)) + op_(')') >> make_tuple
    fx_app      = (op_('(') + fx_anon + op_(')') | name) + tuple_ >> make_application

    yaffel      = evaluable + skip(finished)
    # yaffel      = fx_anon

    # tokenize and parse the given sequence
    parsed = yaffel.parse(tokenize(seq))
    return (type(parsed), parsed)

if __name__ == '__main__':
    #print(tokenize(sys.argv[1]))
    print( '%s %s' % parse(sys.argv[1]) )
    #print( parse(sys.argv[1])[1](**{'x':24}) )
