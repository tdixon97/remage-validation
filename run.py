from __future__ import annotations

import numpy as numpy
import utils
import time
import subprocess
import yaml


def run_simulation(
    replacements: dict, out_path: str, keywords: dict, *, threads: int = 8
) -> bool:
    """Run a remage simulation.

    Parameters
    ----------
    generator
        the macro commands to generate primaries.
    replacements
        set of values for replacements to use.
    out_path
        output path for the files
    """

    # make the folder
    utils.setup_folder(out_path)

    # make the macro
    macro = f"{out_path}/config/macro.mac"
    out = f"{out_path}/stp/out.lh5"

    stats_file = f"{out_path}/stats/stats.yaml"
    log = f"{out_path}/log/log.txt"

    utils.make_macro("config/macro.mac", replacements, macro)

    keyword_string = utils.get_keywords_string(keywords)

    start_time = time.time()
    subprocess.run(
        f"remage {macro} -g config/geometry.gdml {keyword_string} -o {out} -w -t {threads}  2>&1 | tee {log}",
        shell=True,
    )

    end_time = time.time()

    # get the stats
    stats = {
        "time": end_time - start_time,
        "size": utils.get_folder_size(f"{out_path}/stp/"),
    }
    # save the stats
    with open(stats_file, "w") as f:
        yaml.dump(stats, f, default_flow_style=False)

    return True
