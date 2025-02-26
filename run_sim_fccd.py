import subprocess
from pathlib import Path
import time
import numpy as np
import shutil
import yaml


def clear_directory(directory):
    path = Path(directory)
    if not path.exists():
        return  # Do nothing if the directory does not exist

    for item in path.iterdir():
        if item.is_file() or item.is_symlink():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


def replace_lines(
    input_file: str, output_file: str, replacements: dict[str, str]
) -> None:
    """Replaces lines in a file that match given patterns.

    Parameters:
    - input_file: Path to the input text file.
    - output_file: Path to save the modified text file.
    - replacements: A dictionary where keys are regex patterns to match lines,
      and values are the replacement strings.
    """
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(output_file, "w", encoding="utf-8") as f:
        for line in lines:
            for pattern, replacement in replacements.items():
                if pattern in line:
                    line = replacement + "\n"
                    break
            f.write(line)


def run_sim(
    generator_name="",
    name="",
    val="0",
    step_limits="",
    prod_cuts="",
    step_points="",
    proc = "",
    generator="",
    register_lar=False,
):
    macro_file = "mac.mac"
    dir_string = f"{generator_name}/{name}/max_{val}/"

    # make the out directory
    stp_directory = Path(f"out/{dir_string}/stp/")
    clear_directory(stp_directory)
    macro_directory = Path(f"macros/{dir_string}/")
    clear_directory(macro_directory)

    lar_command = (
        "/RMG/Geometry/RegisterDetector Scintillator LAr 002" if register_lar else ""
    )

    stp_directory.mkdir(parents=True, exist_ok=True)
    macro_directory.mkdir(parents=True, exist_ok=True)

    replacements = {
        "$STEP_LIMITS_COMMAND": step_limits,
        "$PROD_CUTS_COMMAND": prod_cuts,
        "$GENERATOR": generator,
        "$STEP_POINT": step_points,
        "$PROC":proc,
        "$REGISTER_LAR": lar_command,
    }
    replace_lines(
        "macros/template.mac", macro_directory / Path(macro_file), replacements
    )

    start = time.time()
    subprocess.run(
        f"remage {macro_directory / macro_file} -g gdml/geometry_fccd.gdml -o {stp_directory}/out.lh5 -w -t 128  ",
        shell=True,
    )
    end = time.time()
    return end - start, get_folder_size(stp_directory)


def get_folder_size(path):
    return f"{(sum(f.stat().st_size for f in Path(path).rglob('*') if f.is_file()) / (1024**2)):.2f}"


do_gamma = False
do_cuts = False
do_bulk = True
do_k42 = True
do_surf = True

generators = {}
cuts = [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500,1000]


# define some generator commands

if (do_am):
    generators["am241"] = """
    /RMG/Generator/Confine Volume
    /RMG/Generator/Confinement/Physical/AddVolume Source
    /RMG/Generator/Select GPS
    /gps/particle ion
    /gps/energy 0 eV
    /gps/ion 95 241 
    """
if (do_ba):
    generators["ba133"] = """
    /RMG/Generator/Confine Volume
    /RMG/Generator/Confinement/Physical/AddVolume Source
    /RMG/Generator/Select GPS
    /gps/particle ion
    /gps/energy 0 eV
    /gps/ion 77 133
    """
    

# with and without the argon table
profile = {}
for generator, config in generators.items():
    profile[generator] = {}

    for proc in ["eBrem","msc","all"]:
        ps = f"/process/inactivate {proc}" if proc!="all" else ""
        for lar in [False]:
            name =f"def_lar_on_{proc}" if lar else f"def_lar_off_{proc}"

            times, size = run_sim(
                generator_name=generator,
                name=name,
                val="0",
                step_points="/RMG/Output/Germanium/StepPositionMode Both",
                prod_cuts="",
                proc =ps,
                generator=config,
                register_lar=lar,
            )

            profile[generator][name] = {"time": f"{times:.1f}", "size": size}
        
        
        profile[generator][f"step_limits_{proc}"] = {}

        # loop over step limits
        for step_limits in cuts:

            times, size = run_sim(
                generator_name=generator,
                name=f"step_limits_{proc}",
                val=step_limits,
                step_limits=f"/RMG/Geometry/SetMaxStepSize {step_limits} um germanium",
                prod_cuts="",
                proc = ps,
                step_points="/RMG/Output/Germanium/StepPositionMode Both",
                generator=config,
                register_lar=False,
            )
            profile[generator][f"step_limits_{proc}"][str(step_limits)] = {
                "time": f"{times:.1f}",
                "size": size,
            }



    # add a production cut in germanium
    if do_cuts:
        for sens_prod_cut in np.linspace(5, 145, 8):
            times, size = run_sim(
                generator_name=generator,
                name="sens_prod_cuts",
                val=int(sens_prod_cut),
                step_limits="",
                prod_cuts=f"/RMG/Processes/SensitiveProductionCut {sens_prod_cut} um",
                generator=config,
                register_lar=False,
            )
            profile[generator]["sens_prod_cuts"][str(sens_prod_cut)] = {
                "time": f"{times:.1f}",
                "size": size,
            }

        # default prod cut (outside)
        for def_prod_cut in np.linspace(10, 490, 5):
            for lar in [True, False]:
                name = "def_prod_cuts_lar_on" if lar else "def_prod_cuts_lar_off"

                times, size = run_sim(
                    generator_name=generator,
                    name=name,
                    val=int(def_prod_cut),
                    step_limits="",
                    prod_cuts=f"/RMG/Processes/DefaultProductionCut {def_prod_cut} um",
                    generator=config,
                    register_lar=lar,
                )
                profile[generator][name][str(def_prod_cut)] = {
                    "time": f"{times:.1f}",
                    "size": size,
                }

with open("out/profile/profile.yaml", "w") as f:
    yaml.dump(profile, f, default_flow_style=False)
