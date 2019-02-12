import matplotlib.pyplot as plt


def worker_out_demo_func(parameter):
    exec(parameter['hyperpar'], globals(), globals())
    plt.switch_backend('agg')
    plt.ioff()
    fig = plt.figure(figsize=(10, 2))
    ax = fig.add_subplot(1, 1, 1)
    ax.scatter(x, y, s=size)
    fig.savefig(parameter['worker_save_path'] + 'scatter_plot.pdf')
    plt.close(fig)

    return x * y + size
