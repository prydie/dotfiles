import os
import sys
import pandas as pd


try:
    from StringIO import StringIO  # # for Python 2
except ImportError:
    from io import StringIO  # # for Python 3


def to_df(xlabel, ylabel):
    return pd.read_csv(sys.stdin, names=[xlabel, ylabel])

def display(title, xlabel, ylabel):
    df = to_df(xlabel, ylabel)
    print(df.to_string())
    df.plot(x=xlabel, y=ylabel, kind="bar")


if __name__ == '__main__':
    title = os.environ.get('TITLE', 'Untitled')
    xlabel = os.environ.get('X_LABEL', 'X')
    ylabel = os.environ.get('Y_LABEL', 'Y')
    display(title, xlabel, ylabel)
