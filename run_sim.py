import subprocess
from pathlib import Path
import time
import numpy as np
import shutil


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
    generator="",
    register_lar=False,
):
    macro_file = "mac.mac"
    dir_string = f"{generator_name}/{name}/max_{val}/"

    # make the out directory
    stp_directory = Path(f"out/{dir_string}/stp/")
    clear_directory(stp_directory)
    macro_directory = Path(f"macros/{dir_string}/")
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
        "$REGISTER_LAR": lar_command,
    }
    replace_lines(
        "macros/template.mac", macro_directory / Path(macro_file), replacements
    )

    start = time.time()
    result = subprocess.run(
        f"remage {macro_directory / macro_file} -g gdml/geometry.gdml -o {stp_directory}/out.lh5 -w  ",
        shell=True,
    )
    end = time.time()
    return end - start, get_folder_size(stp_directory)


def get_folder_size(path):
    return f"{(sum(f.stat().st_size for f in Path(path).rglob('*') if f.is_file()) / (1024**2)):.2f}"


generators = {}

# define some generator commands
generators["beta_surf"] = """
/RMG/Generator/Select GPS
/gps/position 0 0 -5 mm
/gps/particle e-
/gps/energy 1000 keV
/gps/direction 0 0 1
"""


generators["beta_bulk"] = """
/RMG/Generator/Confine Volume
/RMG/Generator/Confinement/Physical/AddVolume germanium
/RMG/Generator/Select GPS
/gps/particle e-
/gps/ang/type iso
/gps/energy 1000 keV
"""

generators["gamma_bulk"] = """
/RMG/Generator/Confine Volume
/RMG/Generator/Confinement/Physical/AddVolume germanium
/RMG/Generator/Select GPS
/gps/particle gamma
/gps/ang/type iso
/gps/energy 1000 keV
"""

generators["gamma_external"] = """
/RMG/Generator/Confine Volume
/RMG/Generator/Confinement/Physical/AddVolume Source
/RMG/Generator/Select GPS
/gps/particle e-
/gps/ang/type iso
/gps/energy 1000 keV
"""


# with and without the argon table
profile = {}
for generator, config in generators.items():
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

        times, size = run_sim(
            generator_name=generator,
            name=name,
            val="0",
            step_limits="",
            prod_cuts="",
            generator=config,
            register_lar=lar,
        )

        profile[generator][name] = {"time": f"{times:.1f}", "size": size}

    # add step limits to Ge

    for step_point in ["PreStep", "PostStep", "Average"]:
        times, size = run_sim(
            generator_name=generator,
            name="step_point",
            val=step_point,
            step_limits=f"/RMG/Output/Germanium/StepPositionMode/{step_point}",
            prod_cuts="",
            generator=config,
            register_lar=False,
        )
        # profile[generator]["step_limits"][str(step_limits)] = {"time":f"{times:.1f}","size":size}

        for step_limits in np.linspace(10, 190, 7):
            times, size = run_sim(
                generator_name=generator,
                name=f"step_limits_{step_point}",
                val=int(step_limits),
                step_limits=f"/RMG/Geometry/SetMaxStepSize {step_limits} um germanium",
                prod_cuts="",
                step_points=f"/RMG/Output/Germanium/StepPositionMode {step_point}",
                generator=config,
                register_lar=False,
            )
            profile[generator]["step_limits"][str(step_limits)] = {
                "time": f"{times:.1f}",
                "size": size,
            }

    """

    # add a production cut in germanium
    for sens_prod_cut in np.linspace(5,145,8):
        times , size = run_sim(
                            generator_name = generator,
                            name = "sens_prod_cuts",
                            val = int(sens_prod_cut),
                            step_limits = "",
                            prod_cuts = f"/RMG/Processes/SensitiveProductionCut {sens_prod_cut} um",
                            generator=config,
                            register_lar = False)
        profile[generator]["sens_prod_cuts"][str(sens_prod_cut)] = {"time":f"{times:.1f}","size":size}

    # default prod cut (outside)
    for def_prod_cut in np.linspace(10,490,5):
        for lar in [True,False]:
            name = "def_prod_cuts_lar_on" if lar else "def_prod_cuts_lar_off"

            times , size = run_sim(
                                generator_name = generator,
                                name = name,
                                val = int(def_prod_cut),
                                step_limits = "",
                                prod_cuts =f"/RMG/Processes/DefaultProductionCut {def_prod_cut} um",
                                generator=config,
                                register_lar = lar)
            profile[generator][name][str(def_prod_cut)] = {"time":f"{times:.1f}","size":size}

with open("profile.yaml", "w") as f:
    yaml.dump(profile, f, default_flow_style=False)
    """
