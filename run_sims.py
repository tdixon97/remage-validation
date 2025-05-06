from __future__ import annotations

import numpy as numpy
import utils
import run
import post_proc

# script to look over production cuts


def run_sims(gen, ranges: list, name: str, field: str, source: str):
    """Run the simulations."""

    for cut in ranges:
        kwargs = {
            "cluster_dist": None,
            "sensitive_cut": 100,
            "step_limit": None,
            "register_lar": False,
            "source": source,
        }
        N = 5000000 if source == "germanium" else 5000000
        # edit the kwargs

        if field == "cuts" and cut is not None:
            kwargs["sensitive_cut"] = cut
        elif field == "steps" and cut is not None:
            kwargs["step_limit"] = cut
        elif field == "cluster" and cut is not None:
            kwargs["cluster_dist"] = cut

        utils.setup_folder(f"out/{name}/", subfolders=[])

        reps = utils.get_replacements(gen, **kwargs)

        run.run_simulation(
            reps, f"out/{name}/cut_{cut}/", {"ENERGY": 1000, "N": N}, threads=8
        )

        post_proc.run_reboost(f"out/{name}/cut_{cut}/", threads=8)


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

gen = utils.get_generator(name="gamma")

run_sims(gen, [None, 10, 20, 50, 100, 200], "gamma_prod_cuts", "cuts", source="Source")
run_sims(
    gen, [None, 10, 20, 50, 100, 200], "gamma_step_limits", "steps", source="Source"
)
run_sims(
    gen, [None, 10, 20, 50, 100, 200], "gamma_cluster_dist", "cluster", source="Source"
)
