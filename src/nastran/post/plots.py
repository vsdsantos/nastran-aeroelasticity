from matplotlib import pyplot as plt
from pandas.core.frame import DataFrame


def plot_complex(df: DataFrame, modes=None):
    fig = plt.figure()
    for point, df in df.groupby(level="POINT"):
        if modes != None and point not in modes:
            continue
        plt.plot(df.REALEIGVAL, df.IMAGEIGVAL, label="Mode {}".format(int(point)), markevery=4)
    fig.legend()
    return fig


def plot_v_f(df: DataFrame, modes=None):
    fig = plt.figure()
    for point, df in df.groupby(level="POINT"):
        if modes != None and (point not in modes):
            continue
        plt.plot(df.VELOCITY, df.FREQUENCY, label="Mode {}".format(int(point)), markevery=4)
    fig.legend()
    return fig


def plot_v_g(df: DataFrame, modes=None):
    fig = plt.figure()
    for point, df in df.groupby(level="POINT"):
        if modes != None and (point not in modes):
            continue
        plt.plot(df.VELOCITY, df.DAMPING, markevery=4)
    fig.legend()
    return fig


def plot_vf_vg(df: DataFrame, modes=None):
    fig, axs = plt.subplots(2)

    for point, df in df.groupby(level="POINT"):

        if modes != None and (point not in modes):
            continue

        axs[0].plot(df.VELOCITY, df.FREQUENCY, label="Mode {}".format(int(point)), markevery=4)
        axs[1].plot(df.VELOCITY, df.DAMPING, markevery=4)

    axs[0].grid()
    axs[1].grid()

    fig.legend()

    return fig
