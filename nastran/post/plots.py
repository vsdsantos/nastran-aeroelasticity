

def plot_vf_vg(df, only_critic=False, epsilon=1e-3):
    fig, axs = plt.subplots(2)

    for point, df in df.groupby(level="POINT"):

        if only_critic and not any(df.DAMPING >= epsilon):
            continue

        axs[0].plot(df.VELOCITY, df.FREQUENCY, label="Mode {}".format(int(point)), markevery=4)
        axs[1].plot(df.VELOCITY, df.DAMPING, markevery=4)

    axs[0].grid()
    axs[1].grid()

    fig.legend()

    return fig
