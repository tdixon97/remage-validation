from __future__ import annotations

import numpy as numpy
import utils
import time
import yaml
import dbetto
from reboost.build_glm import build_glm
from reboost.build_hit import build_hit
from reboost.utils import get_file_list


def run_reboost(
    file_path: str, reboost_config: str = "config/hit_config.yaml", threads: int = 128
):
    """Run the reboost post processing.

    Parameters
    ----------
    file_path
        path to the folder with the stp files
    reboost_config
        path to the config file
    threads
        number of threads used
    """
    stats_file = f"{file_path}/stats/stats_post.yaml"

    t = time.time()

    glm_files = get_file_list(f"{file_path}/glm/out.lh5", threads=threads)
    stp_files = get_file_list(f"{file_path}/stp/out.lh5", threads=threads)
    hit_files = get_file_list(f"{file_path}/hit/out.lh5", threads=threads)

    build_glm(
        glm_files=glm_files,
        stp_files=stp_files,
        id_name="evtid",
    )

    args = dbetto.AttrsDict({"gdml": "config/geometry.gdml"})

    _, _ = build_hit(
        reboost_config,
        args=args,
        stp_files=stp_files,
        glm_files=glm_files,
        hit_files=hit_files,
        buffer=10_000_000,
    )

    end_time = time.time()
    stats = {
        "time": end_time - t,
        "size": utils.get_folder_size(f"{file_path}/hit/"),
    }
    # save the stats
    with open(stats_file, "w") as f:
        yaml.dump(stats, f, default_flow_style=False)

    return True
