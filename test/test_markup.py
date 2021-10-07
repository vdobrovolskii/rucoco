import pytest

from coref_markup.markup import Markup


def test_add_entity():
    m = Markup()
    a, b, c, d, e = (0, 1), (2, 3), (4, 5), (6, 7), (8, 9)
    m.merge(a, b)
    assert m.entities == [[a, b]]
    m.merge(a, c)
    assert m.entities == [[a, b, c]]
    m.merge(d, e)
    assert m.entities == [[a, b, c], [d, e]]
    m.merge(a, e)
    assert m.entities == [[a, b, c, d, e]]


def test_already_merged():
    m = Markup()
    a, b = (0, 1), (2, 3)
    m.merge(a, b)
    with pytest.raises(AssertionError):
        m.merge(a, b)
