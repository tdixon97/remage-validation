from __future__ import annotations
import os
import shutil
import yaml
import numpy as np
import awkward as ak
from lgdo import lh5
import copy
from pathlib import Path
from scipy.stats import beta, poisson, norm
import hist


def get_cylinder_dist(r: np.ndarray, z: np.ndarray, radius: float, height: float):
    """Get distance to surface for a cylinder."""
    a = np.array((height / 2.0 - z).to_numpy())
    b = np.array((z + height / 2).to_numpy())
    c = np.array((radius - r).to_numpy())

    return np.minimum(np.minimum(a, b), c)


def get_lh5(
    generator: str,
    name: str,
    val: float,
    dist_low: float | None = None,
    dist_high: float | None = None,
):
    """Get the data from an lh5 file.

    Parameters
    ----------
    generator
        name of the generator
    name
        name of the simulation
    val
        value of the cut
    dist_low
        low cut on distance to surface for the vertices
    dist_high
        high cut on distance to surface
    """
    height = 40  # mm
    radius = 40  # mm

    path = f"{generator}_{name}_{val}/"
    hit_directory = Path(f"out/{path}/hit/")
    files = hit_directory.glob("*.lh5")

    data = None
    verts = None

    for file in files:
        data_tmp = lh5.read_as("det001/hit", f"{file}", "ak")
        verts_tmp = lh5.read_as("vertices/hit", f"{file}", "ak")

        verts_tmp["dist_to_surf"] = get_cylinder_dist(
            1000 * verts_tmp.rloc, 1000 * verts_tmp.zloc, radius, height
        )
        hit_ids = np.array(np.searchsorted(verts_tmp.first_evtid, data_tmp.first_evtid))
        verts_tmp = verts_tmp[hit_ids]

        if data is not None:
            data = ak.concatenate((data, data_tmp))
            verts = ak.concatenate((verts, verts_tmp))
        else:
            data = copy.deepcopy(data_tmp)
            verts = copy.deepcopy(verts_tmp)

    if dist_low is not None:
        n_sel = ak.sum(
            ak.flatten(
                (verts["dist_to_surf"] > dist_low) & (verts["dist_to_surf"] < dist_high)
            )
        )
    else:
        n_sel = len(verts)

    data["vert_rloc"] = 1000 * ak.flatten(verts.rloc)
    data["vert_zloc"] = 1000 * ak.flatten(verts.zloc)

    data["vert_dist_to_surf"] = get_cylinder_dist(
        data.vert_rloc, data.vert_zloc, radius, height
    )

    if dist_low is not None:
        data = data[
            (data["vert_dist_to_surf"] > dist_low)
            & (data["vert_dist_to_surf"] < dist_high)
        ]

    return data, n_sel


def get_binomial_interval(npass: float, n: float):
    """Extract an interval of a binomial distribution.

    Parameters
    ----------
    npass
        number of events passing
    n
        total number of events

    Returns
    -------
    tuple of (err_low,err_high)
    """

    eff = npass / n
    quantiles = beta.ppf([0.16, 0.84], npass + 1, n - npass + 1)
    err_low = eff - quantiles[0]
    err_high = quantiles[1] - eff
    if err_high <= 0:
        quantiles = beta.ppf([1 - 0.68, 1], npass + 1, n - npass + 1)
        err_low = eff - quantiles[0]
        err_high = quantiles[1] - eff
    elif err_low <= 0:
        quantiles = beta.ppf([0, 0.68], npass + 1, n - npass + 1)
        err_low = eff - quantiles[0]
        err_high = quantiles[1] - eff
    return err_low, err_high


def norm_histo(histo: hist.Hist, bins: list):
    """Normalise a histogram."""
    c, bc = histo.to_numpy()
    left = bc
    centers = []
    counts = copy.deepcopy(c)
    for b in range(histo.size - 2):
        histo[b] *= 1 / np.diff(bins)[b]
        centers.append(left[b] + np.diff(bins)[b] / 2.0)
    return counts, centers


def normalized_poisson_residual(mu1: float, mu2: float) -> np.ndarray:
    """Compute a normalised poisson residual between two poisson distributed
    random variables.

    This is based on computing the distribution of the difference N1-N2
    and finding the tail probability i.e. the fraction of the
    distribution < 0 or > 0. I.e. the residual represents the number of
    sigma the difference N1-N2 is from 0.

    In the case of high count rates the distribution is approximated as
    Gaussian.
    """

    if mu1 == 0 or mu2 == 0:
        return 0

    if mu1 > 10 and mu2 > 10:
        return (mu1 - mu2) / np.sqrt(mu1 + mu2)

    N = 100_000
    samples = poisson.rvs(mu=float(mu1), size=N) - poisson.rvs(mu=float(mu2), size=N)
    counts = sum(samples > 0)

    if counts < N / 2.0:
        sign = -1
        prob = counts / N
    else:
        sign = 1
        counts = N - counts
        prob = (counts) / N
    if prob == 0:
        prob = 1e-5
    return sign * norm.ppf(1 - prob)


def get_hist(ak_obj: ak.Array, field: str, bins_tmp: list):
    """Get the histogram."""
    ak_obj = ak_obj[ak_obj[field] != 0]
    ak_obj[field] = ak_obj[field]

    return hist.Hist(hist.axis.Variable(bins_tmp)).fill(ak_obj[field].to_numpy() + 1e-4)


def get_bins(list_range: list, list_binning: list, e_max: float = 1000):
    """Extract a variable binning."""

    # Define bin ranges
    bin_list = []
    for r, b in zip(list_range, list_binning):
        bin_list.append(np.arange(r[0] * e_max / 1000, r[1] * e_max / 1000, b))

    return np.unique(np.concatenate(bin_list))


def get_folder_size(path: str):
    """Get the size of a folder in MB."""

    folder_path = Path(path)
    size_in_bytes = sum(
        f.stat().st_size for f in folder_path.rglob("*.lh5") if f.is_file()
    )
    return size_in_bytes / (1024 * 1024)  # size in MB"


def get_generator(generator_file: str = "config/generators.yaml", name: str = "beta"):
    """Get the generator from the tabulated YAML file.

    Parameters
    ----------
    generator_file
        the path to the file with generators
    name
        name of the generator to use.
    """
    with open(generator_file, "r") as file:
        data = yaml.safe_load(file)

    return data[name]


def get_replacements(
    generator: list[str],
    *,
    cluster_dist: float | None = None,
    sensitive_cut: float = 100,
    step_limit: float | None = None,
    register_lar: bool = False,
    source: str = "Source",
):
    """Get the replacements dictionary.

    Parameters
    ----------
    generator
        the event generator commands to use.
    cluster_dist
        Distance for preclustering (in um)
    sensitive_cut
        the value of the production cut (in um)
    step_limit
        the value of the step limit, if `None` no step limits are used (in um)
    register_lar
        boolean flag to register the LAr detector
    source
        name of the volume to generate events in.
    """

    # get cluster distance
    if cluster_dist is not None:
        cluster = "/RMG/Output/Germanium/Cluster/PreClusterOutputs \n"
        cluster += (
            f"/RMG/Output/Germanium/Cluster/PreClusterDistance {cluster_dist} um \n"
        )
        cluster += "/RMG/Output/Germanium/Cluster/CombineLowEnergyElectronTracks \n"
        cluster += "/RMG/Output/Germanium/Cluster/RedistributeGammaEnergy "
    else:
        cluster = ""

    # get register lar
    lar_command = (
        ""
        if not register_lar
        else "/RMG/Geometry/RegisterDetector Scintillator LAr 002"
    )
    step_limit_command = (
        ""
        if step_limit is None
        else f"/RMG/Geometry/SetMaxStepSize {step_limit} um germanium"
    )

    confine = "/RMG/Generator/Confine Volume\n"
    confine += f"/RMG/Generator/Confinement/Physical/AddVolume {source}"

    gen = "\n".join(generator)

    return {
        "$PRECLUSTER": cluster,
        "$PROD_CUTS_COMMAND": f"/RMG/Processes/SensitiveProductionCut {sensitive_cut} um",
        "$REGISTER_LAR": lar_command,
        "$STEP_LIMITS_COMMAND": step_limit_command,
        "$GENERATOR": gen,
        "$CONFINE": confine,
    }


def setup_folder(
    base_folder: str, subfolders: list = ["stp", "hit", "glm", "log", "stats", "config"]
):
    """Make a folder and the subfolders, clearing it if it already exists.

    Parameters
    ----------
    base_folder
        Folder to create
    """

    # If the folder exists, remove it and its contents
    if os.path.exists(base_folder):
        shutil.rmtree(base_folder)

    # Create the base folder
    os.makedirs(base_folder)

    # Create the subfolders
    for sub in subfolders:
        os.makedirs(os.path.join(base_folder, sub))


def get_keywords_string(keywords: dict):
    """Get the string of keywords."""

    ret = "-s "

    for key, val in keywords.items():
        ret += f"{key}={val} "
    return ret


def make_macro(template: str, replacements: dict, output: str) -> None:
    """Create the macro file.

    Parameters
    ----------
    template
        Path to the templateee macro
    replacements
        Dictionary of replacements to make.
    output
        Path to the output file.
    """

    if os.path.exists(output):
        os.remove(output)

    with open(template, "r", encoding="utf-8") as f:
        lines = f.readlines()

        with open(output, "w", encoding="utf-8") as f:
            for line in lines:
                for pattern, replacement in replacements.items():
                    if pattern in line:
                        line = replacement + "\n"
                        break

                f.write(line)
