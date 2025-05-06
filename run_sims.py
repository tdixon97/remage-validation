from __future__ import annotations

import numpy as numpy
import utils
import run
import post_proc
import shutil
import colorlog
import logging

# script to look over production cuts

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter("%(log_color)s%(name)s [%(levelname)s] %(message)s")
)
logger = logging.getLogger()
logger.handlers.clear()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def run_sims(gen, ranges: list, name: str, field: str, source: str):
    """Run the simulations."""
    
    utils.setup_folder(f"out/{name}/", subfolders=[])

    for cut in ranges:
        kwargs = {
            "cluster_dist": None,
            "sensitive_cut": 100,
            "step_limit": None,
            "register_lar": False,
            "source": source,
        }
        N = 1000000 if source == "germanium" else 5000000
        # edit the kwargs

        if field == "cuts" and cut is not None:
            kwargs["sensitive_cut"] = cut
        elif field == "steps" and cut is not None:
            kwargs["step_limit"] = cut
        elif field == "cluster" and cut is not None:
            kwargs["cluster_dist"] = cut


        reps = utils.get_replacements(gen, **kwargs)

        run.run_simulation(
            reps, f"out/{name}/cut_{cut}/", {"ENERGY": 1000, "N": N}, threads=8
        )

        post_proc.run_reboost(f"out/{name}/cut_{cut}/", threads=8)

        # remove the stp files
        shutil.rmtree(f"out/{name}/cut_{cut}/stp/")


gen = utils.get_generator(name="beta")

# run_sims(gen,[None, 10, 20,50, 100, 200], "beta_prod_cuts", "cuts",source = "germanium")
# run_sims(gen,[None, 10, 20, 50, 100, 200], "beta_step_limits", "steps",source = "germanium")
run_sims(
    gen,
    [None, 10, 20, 50, 100, 200],
    "beta_cluster_dist",
    "cluster",
    source="germanium",
)
"""Gen = utils.get_generator(name="gamma")

run_sims(gen, [None, 10, 20, 50, 100, 200], "gamma_prod_cuts", "cuts",
source="Source") run_sims(     gen, [None, 10, 20, 50, 100, 200],
"gamma_step_limits", "steps", source="Source" ) run_sims(     gen,
[None, 10, 20, 50, 100, 200], "gamma_cluster_dist", "cluster",
source="Source" )
"""
