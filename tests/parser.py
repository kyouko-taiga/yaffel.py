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

import math, unittest

from yaffel.datatypes import *
from yaffel.exceptions import *
from yaffel.parser import parse

class TestParser(unittest.TestCase):

    def test_int(self):
        self.assertEqual(parse('1'), (int, 1))
        self.assertEqual(parse('-1'), (int, -1))
        self.assertEqual(parse('0'), (int, 0))
        self.assertEqual(parse('-0'), (int, 0))

    def test_float(self):
        self.assertEqual(parse('1.0'), (float, 1.0))
        self.assertEqual(parse('-1.0'), (float, -1.0))
        self.assertEqual(parse('0.0'), (float, 0.0))
        self.assertEqual(parse('-0.0'), (float, 0.0))

    def test_elementary_arithmetic(self):
        self.assertEqual(parse('1 + 1'), (int, 2))
        self.assertEqual(parse('1 + (1 + 2)'), (int, 4))
        self.assertEqual(parse('1 - 1 - 3'), (int, -3))
        self.assertEqual(parse('1 - (1 - 3)'), (int, 3))

        self.assertEqual(parse('1 + 1 * 2'), (int, 3))
        self.assertEqual(parse('(1 + 1) * 2'), (int, 4))
        self.assertEqual(parse('(1 + 1) / 2'), (float, 1.0))
        self.assertRaises(ZeroDivisionError, parse, '(1 + 1) / 0')

    def test_boolean_constant(self):
        self.assertEqual(parse('True'), (bool, True))
        self.assertEqual(parse('False'), (bool, False))

    def test_numeric_predicate(self):
        self.assertEqual(parse('1 == 1'), (bool, True))
        self.assertEqual(parse('1 == 2'), (bool, False))
        self.assertEqual(parse('1 != 2'), (bool, True))
        self.assertEqual(parse('1 != 1'), (bool, False))
        self.assertEqual(parse('1 >= 1'), (bool, True))
        self.assertEqual(parse('1 >= 2'), (bool, False))
        self.assertEqual(parse('2 > 1'), (bool, True))
        self.assertEqual(parse('1 > 1'), (bool, False))
        self.assertEqual(parse('1 <= 1'), (bool, True))
        self.assertEqual(parse('2 <= 1'), (bool, False))
        self.assertEqual(parse('1 < 2'), (bool, True))
        self.assertEqual(parse('1 < 1'), (bool, False))

        self.assertEqual(parse('x == 1 for x = 1'), (bool, True))
        self.assertEqual(parse('1 == x for x = 1'), (bool, True))
        self.assertEqual(parse('x == x for x = 1'), (bool, True))

    def test_string_predicate(self):
        self.assertEqual(parse('"a" == "a"'), (bool, True))
        self.assertEqual(parse('"a" == "b"'), (bool, False))
        self.assertEqual(parse('"a" != "b"'), (bool, True))
        self.assertEqual(parse('"a" != "a"'), (bool, False))
        self.assertEqual(parse('"あ" == "あ"'), (bool, True))

        self.assertEqual(parse('x == "a" for x = "a"'), (bool, True))
        self.assertEqual(parse('"a" == x for x = "a"'), (bool, True))
        self.assertEqual(parse('x == x for x = "a"'), (bool, True))

    def test_set_predicate(self):
        self.assertEqual(parse('{2,1} == {1,2}'), (bool, True))
        self.assertEqual(parse('{1,2} == {2,3}'), (bool, False))
        self.assertEqual(parse('{1,2} != {2,3}'), (bool, True))
        self.assertEqual(parse('{2,1} != {1,2}'), (bool, False))

        self.assertEqual(parse('{1:2} == {1:2}'), (bool, True))
        self.assertEqual(parse('{1:2} == {2:3}'), (bool, False))
        self.assertEqual(parse('{1:2} != {2:3}'), (bool, True))
        self.assertEqual(parse('{1:2} != {1:2}'), (bool, False))

        self.assertEqual(parse('{x for x in {1}} == {x for x in {1}}'), (bool, True))
        self.assertEqual(parse('{x for x in {1}} == {x for x in {2}}'), (bool, False))
        self.assertEqual(parse('{x for x in {1}} != {x for x in {2}}'), (bool, True))
        self.assertEqual(parse('{x for x in {1}} != {x for x in {1}}'), (bool, False))

        self.assertEqual(parse('x == {1} for x = {1}'), (bool, True))
        self.assertEqual(parse('{1} == x for x = {1}'), (bool, True))
        self.assertEqual(parse('x == x for x = {1}'), (bool, True))

    def test_exponent(self):
        self.assertEqual(parse('2 ** 2'), (int, 4))
        self.assertEqual(parse('2 ** 3'), (int, 8))
        self.assertEqual(parse('2 ** 0.5'), (float, 2 ** 0.5))

        self.assertEqual(parse('2 ** 2 ** 3'), (int, 64))
        self.assertEqual(parse('2 ** (2 ** 3)'), (int, 256))

    def test_variable_bounding(self):
        self.assertEqual(parse('x for x = 1'), (int, 1))
        self.assertEqual(parse('x for x = 1.0'), (float, 1.0))
        self.assertEqual(parse('x + x for x = -1.0'), (float, -2.0))

        self.assertEqual(parse('x for x = y for y = 1'), (int, 1))
        self.assertEqual(parse('x for x = x for x = 1'), (int, 1))
        self.assertEqual(parse('x for x =(x for x = 1)'), (int, 1))

        self.assertRaises(EvaluationError, parse, 'x')
        self.assertRaises(EvaluationError, parse, 'x + y for x = 1')

    def test_enumeration_expression(self):
        self.assertEqual(parse('{}'), (Enumeration, Enumeration([])))
        self.assertEqual(parse('{1}'), (Enumeration, Enumeration([1])))
        self.assertEqual(parse('{1,2}'), (Enumeration, Enumeration([1,2])))

        self.assertEqual(parse('{x} for x = 1'), (Enumeration, Enumeration([1])))
        self.assertEqual(parse('{1,x} for x = 1'), (Enumeration, Enumeration([1])))
        self.assertEqual(parse('{x+1} for x = 1'), (Enumeration, Enumeration([2])))
        self.assertEqual(parse('{{}}'), (Enumeration, Enumeration([Enumeration([])])))

    def test_range_expression(self):
        self.assertEqual(parse('{0:10}'), (Range, Range(0,10)))
        self.assertEqual(parse('{-5:5}'), (Range, Range(-5,5)))
        self.assertEqual(parse('{-10:-1}'), (Range, Range(-10,-1)))

        self.assertRaises(TypeError, parse, '{1:0}')
        self.assertRaises(TypeError, parse, '{1:1}')
        self.assertRaises(SyntaxError, parse, '{1:{1:2}}')

    def test_set_expression(self):
        t, s = parse('{x for x in {}}')
        self.assertEqual(t, Set)

        # ...

    def test_function_application(self):
        self.assertEqual(parse('log(8)'), (float, math.log(8)))
        self.assertEqual(parse('log(8,2)'), (float, math.log(8,2)))

    def test_anonymous_function(self):
        self.assertEqual(parse('[:1]()'), (int, 1))
        self.assertEqual(parse('[x: x](1)'), (int, 1))
        self.assertEqual(parse('[x: x + 1](1)'), (int, 2))
        self.assertEqual(parse('[x, y: x + y](1, 2)'), (int, 3))
        self.assertEqual(parse('[x: x + 1 if x < 5 else x](4)'), (int, 5))
        self.assertEqual(parse('[x: x + 1 if x < 5 else x](5)'), (int, 5))

        self.assertEqual(parse('g(1) for g=[x: x]'), (int, 1))
        self.assertEqual(parse('g(y) for g=[x: x], y=2'), (int, 2))
        self.assertEqual(parse('g(y,z) for g=[a, b: a + b], y=2, z=3'), (int, 5))

        self.assertEqual(parse('g() for g=[:1]'), (int, 1))
        self.assertEqual(parse('g(1) for g=[x:log(x)]'), (float, 0.0))

        # fixed point
        self.assertEqual(parse('fp([x:x+1 if x < 10 else 10], 4)' +
                               'for fp=[f,x: x if f(x)==x else fp(f, f(x))]'), (int, 10))

        self.assertRaises(EvaluationError, parse, 'g(x)')
        self.assertRaises(TypeError, parse, '[x, y: x](1)')

if __name__ == '__main__':
    unittest.main()
