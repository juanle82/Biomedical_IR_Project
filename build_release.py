import os
import time
import shutil
from string import Template
import PyInstaller.__main__
import git


def cmd_message(msg):
    print(
        f"\n===================================================== \
          \n\n{msg} \
          \n\n====================================================="
    )


if __name__ == "__main__":
    version_filename = "version.txt"
    spec_filename = "VisionBio.spec"
    spec_template_filename = "VisionBio_spec_template.txt"

    # Deletes current version.txt file
    if os.path.exists(version_filename):
        os.remove(version_filename)

    # Delete current VisionBio.spec file
    if os.path.exists(spec_filename):
        os.remove(spec_filename)

    # Writes latest git version info to 'version.txt'
    r = git.repo.Repo(search_parent_directories=True)
    version_info = r.git.describe("--dirty", "--tags")
    with open(version_filename, "w") as f:
        f.write(version_info)
        f.write("\n")
        f.close()

    cmd_message("Installing Linux dependences...")
    os.system("sudo apt update && sudo apt upgrade -y")
    os.system("sudo apt install libopenblas-dev")

    cmd_message("Installing python modules...")
    os.system("python -m pip install --upgrade pip")
    os.system("python -m pip install -r requirements.txt")

    # Write the new VisionBio.spec from the template
    data = {"version_file": version_filename, "version": version_info}
    with open(spec_template_filename, "r") as f, open(spec_filename, "w") as fout:
        template = f.read()
        filled_template = Template(template).safe_substitute(data)
        fout.write(filled_template)
        fout.write("\n")
        fout.close()

    # Builds production version
    cmd_message(f"Building release VisionBio-{version_info}")
    time.sleep(2)
    PyInstaller.__main__.run(["--clean", "--noconfirm", "VisionBio.spec"])

    # Copy files to release folder
    cmd_message(f"Creating release folder for VisionBio-{version_info}")
    if os.path.exists("dist/main"):
        release_path = f"releases/{version_info}"
        # Remove corresponding release folder if exists
        if os.path.exists(release_path):
            shutil.rmtree(release_path)
        shutil.copytree("dist/main", release_path)

    cmd_message("Release build complete.")
