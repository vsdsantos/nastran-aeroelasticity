import pytest

from nastran.post.f06 import read_f06
from nastran.post.flutter import join_flutter_pages, flutter_pages_to_df, get_critical_roots, FlutterF06Page


@pytest.fixture
def flutter_f06():
    return read_f06('tests/files/flutter-f06-result.txt')


@pytest.fixture
def flutter_pages(flutter_f06):
    return flutter_f06.flutter


@pytest.fixture
def flutter_pages_joint(flutter_pages):
    return join_flutter_pages(flutter_pages)


@pytest.fixture
def flutter_pages_df(flutter_pages_joint):
    return flutter_pages_to_df(flutter_pages_joint)


@pytest.fixture
def flutter_pages_df_critic(flutter_pages_df):
    return get_critical_roots(flutter_pages_df)


def test_read_f06(flutter_f06):
    assert flutter_f06.pages != None
    assert len(flutter_f06.pages) == 70


def test_flutter_results1(flutter_pages):
    assert all(map(lambda p: type(p) == FlutterF06Page, flutter_pages))
    assert len(flutter_pages) == 30


def test_flutter_results2(flutter_pages_joint):
    assert len(flutter_pages_joint) == 15


def test_flutter_results3(flutter_pages_joint, flutter_pages_df):
    assert len(flutter_pages_df) == sum(map(lambda p: len(p.df), flutter_pages_joint))


def test_flutter_results4(flutter_pages_df_critic):
    assert len(flutter_pages_df_critic) == 1
