import pandas as pd
import numpy as np
from pandas.core.frame import DataFrame

class F06Page:

    def __init__(self, meta=None):
        self.meta = meta

def extract_tabulated_data(lines):
    data = []
    for line in lines:
        entries = line.split()
        inner_data = []
        for entry in entries:
            try:
                e = float(entry)
            except ValueError:
                e = np.nan
            finally:
                inner_data.append(e)
        data.append(inner_data)
    return data

def parse_text_value(value):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


# def read_and_concat_f06s(case_files, labels, label_name="THETA"):
#
#     if len(labels) != len(case_files):
#         raise Exception("Collections should be of same size.")
#
#     df_results = []
#
#     for i, fn in enumerate(case_files):
#         print("Reading... {}".format(fn))
#         df_data = read_f06(fn)
#         df_results.append(
#             pd.concat(
#                 { labels[i]: df_data },
#                 names=[label_name]
#             )
#         )
#
#     return pd.concat(df_results)
