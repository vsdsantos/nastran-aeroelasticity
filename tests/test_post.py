import pytest

from nastran.post.f06 import read_f06
from nastran.post.flutter import join_flutter_pages, flutter_pages_to_df, get_critical_roots, FlutterF06Page

def test_read_f06():
    f06 = read_f06('tests/files/flutter-f06-result.txt')
    assert f06.pages != None
    assert len(f06.pages) > 0

def test_flutter_results1():
    f06 = read_f06('tests/files/flutter-f06-result.txt')
    only_flutter = f06.flutter
    assert all(map(lambda p: type(p) == FlutterF06Page, only_flutter))

def test_flutter_results2():
    f06 = read_f06('tests/files/flutter-f06-result.txt')
    only_flutter = f06.flutter
    reduced_flutter = join_flutter_pages(only_flutter)
    assert len(only_flutter) >= len(reduced_flutter)

def test_flutter_results3():
    f06 = read_f06('tests/files/flutter-f06-result.txt')
    only_flutter = f06.flutter
    reduced_flutter = join_flutter_pages(only_flutter)
    df = flutter_pages_to_df(reduced_flutter)
    assert len(df) == sum(map(lambda p: len(p.df), reduced_flutter))

def test_flutter_results4():
    f06 = read_f06('tests/files/flutter-f06-result.txt')
    only_flutter = f06.flutter
    reduced_flutter = join_flutter_pages(only_flutter)
    df = flutter_pages_to_df(reduced_flutter)
    df_cr = get_critical_roots(df)
    assert len(df_cr) == 1
