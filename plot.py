from __future__ import annotations


import numpy as np
from matplotlib import pyplot as plt
import tol_colors as tc
import awkward as ak
import dbetto
import utils

plt.rcParams["lines.linewidth"] = 1
plt.rcParams["figure.figsize"] = (12, 4)
plt.rcParams["font.size"] = 14
vib = tc.tol_cset("vibrant")
vset = tc.tol_cset("vibrant")
mset = tc.tol_cset("muted")

style = {
    "yerr": False,
    "flow": None,
    "fill": False,
    "lw": 1,
}

# Get the BuPu colormap
cmap = plt.get_cmap("cividis")


def plot_residual(ax, label, bin_centers: list, def_counts: list, low_counts: list):
    resid = np.array(
        [
            utils.normalized_poisson_residual(mu, obs)
            for mu, obs in zip(def_counts, low_counts)
        ]
    )
    ax.axhspan(-3, 3, color="red", alpha=0.2)
    ax.axhspan(-2, 2, color="gold", alpha=0.2)
    ax.axhspan(-1, 1, color="green", alpha=0.2)

    ax.errorbar(bin_centers, resid, fmt=".", color="black")
    ax.set_xlabel(label)
    ax.set_ylabel("Resid")
    ax.set_ylim(
        -max(np.max(abs(resid)), 4.9) - 0.1, +max(np.max(abs(resid)), 4.9) + 0.1
    )


def make_axes(figsize: tuple):
    """Make the axes for plotting."""
    fig, axs = plt.subplots(
        2,
        1,
        gridspec_kw={"height_ratios": [4, 1], "hspace": 0},
        figsize=figsize,
        sharex=True,
    )
    return [axs]


def get_axis(a):
    return a[0] if not isinstance(a, plt.Axes) else a


def plot(
    generator: str,
    name: str,
    xrange: tuple,
    cuts: list,
    field: str,
    scale: str = "log",
    ylims: tuple | None = None,
    eff_range: tuple = (999, 1001),
    dist_range: tuple | None = None,
    doeff: bool = False,
    figsize: tuple = (12, 4),
    legend: bool = True,
    n_bins: int | None = None,
    bins: list | None = None,
    label="Energy [keV]",
    save_spec_name="spec.png",
    save_eff_name="eff.png",
):
    """Plot the value of the observable.

    Parameters
    ----------
    generator
        the name of the generator
    name
        name of the simulatuion
    xrange
        range for the xaxis
    cuts
        list of cut values
    field
        field to plot
    scale
        scale for the plot yaxis
    """
    bins_tmp = np.linspace(xrange[0], xrange[1], n_bins) if n_bins is not None else bins

    if dist_range is None:
        dist_low = None
        dist_high = None
    else:
        dist_low = dist_range[0]
        dist_high = dist_range[1]

    results = {}

    # get the data
    ak_obj, n_sel = utils.get_lh5(
        generator, name, None, dist_low=dist_low, dist_high=dist_high
    )

    # save the results
    results["def"] = {"n": n_sel, "eff": 0}

    # fill the histogram
    hist_def = utils.get_hist(ak_obj, field, bins_tmp)
    def_counts, bin_centers = utils.norm_histo(hist_def, bins_tmp)

    # get the efficiency
    eff = ak.sum((ak_obj[field] > eff_range[0]) & (ak_obj[field] < eff_range[1]))
    # save the results
    results["def"] = {"n": n_sel, "eff": eff}

    # add a zoom
    axes_list = make_axes(figsize)

    # plot
    for a in axes_list:
        a_tmp = get_axis(a)
        hist_def.plot(
            ax=a_tmp,
            yerr=False,
            flow=None,
            fill=True,
            alpha=0.2,
            color=vib.blue,
            label="No limits",
        )

    for idx, val in enumerate(cuts):
        results[val] = {}
        # get the data
        ak_obj, n_sel = utils.get_lh5(
            generator, name, val, dist_low=dist_low, dist_high=dist_high
        )

        results[val]["n"] = n_sel

        # get the histogram
        hist_tmp = utils.get_hist(ak_obj, field, bins_tmp)
        counts, _ = utils.norm_histo(hist_tmp, bins_tmp)

        # save some info
        if idx == 0:
            low_counts = counts

        if idx == 0 or idx == len(cuts) - 2:
            for a in axes_list:
                a_tmp = get_axis(a)
                hist_tmp.plot(ax=a_tmp, **style, label=f"{val} um ")

            ax = axes_list[0][0]
            if legend:
                ax.legend(loc="upper right")
                ax.legend(ncol=1)
                ax.get_legend().set_title(name)

            ax.set_yscale(scale)
            ax.set_xlabel(label)
            ax.set_ylabel("counts")
            ax.set_xlim(*xrange)

            if ylims is not None:
                ax.set_ylim(*ylims)

        results[val]["eff"] = ak.sum(
            (ak_obj[field] > eff_range[0]) & (ak_obj[field] < eff_range[1])
        )

        plt.tight_layout()

        # plot the residual
        plot_residual(
            axes_list[0][1],
            label,
            bin_centers=bin_centers,
            def_counts=def_counts,
            low_counts=low_counts,
        )

        plt.tight_layout()
        if save_spec_name is not None:
            plt.savefig(save_spec_name)

        if not doeff:
            return

    # plot the efficiency
    plot_efficiency(label, name, save_eff_name, results, eff_range)


def plot_efficiency(
    label: str, name: str, save_eff_name: str | None, results: dict, eff_range: list
):
    """Plot the efficiency."""

    colors = [vib.blue, vib.orange, vib.magenta, vib.teal, vib.grey, vib.cyan]

    fig, ax = plt.subplots()

    eff_def_low = (
        100 * utils.get_binomial_interval(results["def"]["eff"], results["def"]["n"])[0]
    )
    eff_def_high = (
        100 * utils.get_binomial_interval(results["def"]["eff"], results["def"]["n"])[1]
    )

    ax.axhspan(
        ymin=100 * results["def"]["eff"] / results["def"]["n"] - eff_def_low,
        ymax=100 * results["def"]["eff"] / results["def"]["n"] + eff_def_high,
        alpha=0.2,
        color=colors[0],
        label="Default",
    )
    ax.axhline(
        y=100 * results["def"]["eff"] / results["def"]["n"],
        linestyle="--",
        color=colors[0],
    )

    s = [val for val in results.keys() if val != "def"]
    e = [results[val]["eff"] for val in results.keys() if val != "def"]
    n = [results[val]["n"] for val in results.keys() if val != "def"]

    err_low = [utils.get_binomial_interval(et, nt)[0] * 100 for et, nt in zip(e, n)]
    err_high = [utils.get_binomial_interval(et, nt)[1] * 100 for et, nt in zip(e, n)]

    ax.errorbar(
        s,
        100 * np.array(e) / np.array(n),
        yerr=[err_low, err_high],
        fmt=".",
        linestyle="--",
        color=colors[0],
    )

    ax.set_xlabel(f"{name} [um]")
    ax.set_ylabel("Fraction of events [%]")
    ax.set_title(f"Fraction of events in {eff_range[0]} - {eff_range[1]} ({label})")

    plt.tight_layout()
    plt.savefig(save_eff_name)


def plot_performance(
    generator: str, cuts: list, name: str = "step_limits", name_plot: str | None = None
):
    size = []
    vals = []
    times = []

    for cut in sorted(cuts):
        prof = dbetto.AttrsDict(
            dbetto.utils.load_dict(f"out/{generator}_{name}_{cut}/stats/stats.yaml")
        )
        if cut is not None:
            size.append(float(prof.size))
            times.append(float(prof.time))
            vals.append(float(cut))
        else:
            size_def = float(prof.size)
            time_def = float(prof.time)

    # sort
    idx = np.argsort(vals)
    size = np.array(size)[idx]
    vals = np.array(vals)[idx]
    times = np.array(times)[idx]

    # Create figure and first axis
    fig, ax1 = plt.subplots()

    # Plot the first dataset (sine wave)
    ax1.plot(vals, times, "b-*")
    ax1.set_xlabel(f"{name} [um]")
    ax1.set_ylabel("time [s]", color="b")
    ax1.tick_params(axis="y", labelcolor="b")
    ax1.axhline(y=time_def, color="b", linestyle="--")
    # Create a second y-axis sharing the same x-axis
    ax2 = ax1.twinx()

    # Plot the second dataset (cosine wave)
    ax2.plot(vals, size, "r--.")

    ax2.set_ylabel("Size [MB]", color="r")

    ax2.tick_params(axis="y", labelcolor="r")
    ax2.axhline(y=size_def, color="r", linestyle="--")

    ax2.set_xscale("linear")

    # Show the plot
    fig.tight_layout()  # Adjust layout

    if name_plot is not None:
        plt.savefig(name_plot)
