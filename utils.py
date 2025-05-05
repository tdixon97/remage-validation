from __future__ import annotations
import os
import shutil
import yaml
from pathlib import Path


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


def setup_folder(base_folder: str):
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
    subfolders = ["stp", "hit", "glm", "log", "stats", "config"]
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
