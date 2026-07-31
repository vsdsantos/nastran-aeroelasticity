import pandas as pd
from matplotlib import pyplot as plt


def plot_complex(df: pd.DataFrame, modes=None):
    fig = plt.figure()
    for point, point_df in df.groupby(level="POINT"):
        if modes is not None and point not in modes:
            continue
        plt.plot(point_df.REALEIGVAL, point_df.IMAGEIGVAL, label=f"Mode {int(point)}", markevery=4)
    fig.legend()
    return fig


def plot_v_f(df: pd.DataFrame, modes=None):
    fig = plt.figure()
    for point, point_df in df.groupby(level="POINT"):
        if modes is not None and (point not in modes):
            continue
        plt.plot(point_df.VELOCITY, point_df.FREQUENCY, label=f"Mode {int(point)}", markevery=4)
    fig.legend()
    return fig


def plot_v_g(df: pd.DataFrame, modes=None):
    fig = plt.figure()
    for point, point_df in df.groupby(level="POINT"):
        if modes is not None and (point not in modes):
            continue
        plt.plot(point_df.VELOCITY, point_df.DAMPING, markevery=4)
    fig.legend()
    return fig


def plot_vf_vg(df: pd.DataFrame, modes=None):
    fig, axs = plt.subplots(2)

    for point, point_df in df.groupby(level="POINT"):
        if modes is not None and (point not in modes):
            continue

        axs[0].plot(point_df.VELOCITY, point_df.FREQUENCY, label=f"Mode {int(point)}", markevery=4)
        axs[1].plot(point_df.VELOCITY, point_df.DAMPING, markevery=4)

    axs[0].grid()
    axs[1].grid()

    fig.legend()

    return fig
