from __future__ import annotations

import numpy as numpy
import utils
import run
import post_proc

# script to look over production cuts


def run_sims(ranges: list, name: str, field: str):
    """Run the simulations."""

    for cut in ranges:
        kwargs = {
            "cluster_dist": None,
            "sensitive_cut": 100,
            "step_limit": None,
            "register_lar": False,
            "source": "germanium",
        }

        # edit the kwargs
        if field == "cuts":
            kwargs["sensitive_cut"] = cut
        elif field == "steps":
            kwargs["step_limit"] = cut
        elif field == "cluster":
            kwargs["cluster_dist"] = cut

        reps = utils.get_replacements(gen, **kwargs)

        run.run_simulation(
            reps, f"out/{name}_{cut}/", {"ENERGY": 1000, "N": 100000}, threads=8
        )

        post_proc.run_reboost(f"out/{name}_{cut}/", threads=8)


gen = utils.get_generator(name="beta")

run_sims([5, 10, 20, 50, 100, 200], "beta_prod_cuts", "cuts")
run_sims([5, 10, 20, 50, 100, 200], "beta_step_limits", "steps")
run_sims([5, 10, 20, 50, 100, 200], "beta_cluster_dist", "cluster")
