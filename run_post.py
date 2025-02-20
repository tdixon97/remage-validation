from pathlib import Path
import time
import numpy as np
import shutil
import dbetto
from reboost.build_glm import build_glm
from reboost.build_hit import build_hit
import colorlog
import logging

log = logging.getLogger(__name__)

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter("%(log_color)s%(name)s [%(levelname)s] %(message)s")
)
logger = logging.getLogger()
logger.handlers.clear()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def clear_directory(directory):
    path = Path(directory)
    if not path.exists():
        return  # Do nothing if the directory does not exist

    for item in path.iterdir():
        if item.is_file() or item.is_symlink():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


def run_reboost(generator_name, name, val, reboost_config="hit_config.yaml"):
    path = f"{generator_name}/{name}/max_{int(val)}/"

    # directories
    stp_directory = Path(f"out/{path}/stp/")
    glm_directory = Path(f"out/{path}/glm/")
    hit_directory = Path(f"out/{path}/hit/")

    # clear glm before running
    clear_directory(glm_directory)
    clear_directory(hit_directory)

    # make the directories
    hit_directory.mkdir(parents=True, exist_ok=True)
    glm_directory.mkdir(parents=True, exist_ok=True)

    build_glm(
        glm_files=f"{glm_directory}/out.lh5",
        stp_files=f"{stp_directory}/out.lh5",
        id_name="evtid",
    )

    args = dbetto.AttrsDict({"gdml": "gdml/geometry.gdml"})
    t = time.time()
    _, _ = build_hit(
        reboost_config,
        args=args,
        stp_files=f"{stp_directory}/out.lh5",
        glm_files=f"{glm_directory}/out.lh5",
        hit_files=f"{hit_directory}/out.lh5",
        buffer=10_000_000,
    )
    return time.time() - t, get_folder_size(hit_directory)


def get_folder_size(path):
    return f"{(sum(f.stat().st_size for f in Path(path).rglob('*') if f.is_file()) / (1024**2)):.3f}"


generators = ["beta_surf", "beta_bulk", "gamma_bulk", "gamma_external"]

# with and without the argon table
profile = {}
for generator in generators:
    profile[generator] = {
        "def_lar_on": {},
        "def_lar_off": {},
        "step_limits": {},
        "sens_prod_cuts": {},
        "def_prod_cuts_lar_on": {},
        "def_prod_cuts_lar_off": {},
    }

    for lar in [True, False]:
        name = "def_lar_on" if lar else "def_lar_off"

        times, size = run_reboost(generator_name=generator, name=name, val=0)

        profile[generator][name] = {"time": f"{times:.3f}", "size": size}

    # add step limits to Ge
    for step_limits in np.linspace(10, 190, 7):
        for step_point in ["PreStep", "PostStep", "Average"]:
            times, size = run_reboost(
                generator_name=generator,
                name=f"step_limits_{step_point}",
                val=step_limits,
            )

        profile[generator]["step_limits"][str(step_limits)] = {
            "time": f"{times:.3f}",
            "size": size,
        }
    """

    # add a production cut in germanium
    for sens_prod_cut in np.linspace(5,145,8):

        times , size = run_reboost(
                           generator_name = generator,
                            name = "sens_prod_cuts",
                            val = sens_prod_cut)

        profile[generator]["sens_prod_cuts"][str(sens_prod_cut)] = {"time":f"{times:.3f}","size":size}

    # default prod cut (outside)
    for def_prod_cut in np.linspace(10,490,5):
        for lar in [True,False]:
            name = "def_prod_cuts_lar_on" if lar else "def_prod_cuts_lar_off"

            times , size = run_reboost(
                           generator_name = generator,
                           name = name,
                           val = def_prod_cut)

            profile[generator][name][str(def_prod_cut)] = {"time":f"{times:.3f}","size":size}

with open("profile_hit.yaml", "w") as f:
    yaml.dump(profile, f, default_flow_style=False)
"""
