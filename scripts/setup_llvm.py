import subprocess as sp
from pathlib import Path
import os

from fire import Fire
from loguru import logger


def setup_llvm(llvm_dir_str: str):
    llvm_dir = Path(llvm_dir_str)
    if not llvm_dir.exists():
        logger.warning(f"LLVM directory {llvm_dir} does not exist.")

        # Download the zip file
        zip_filename = "llvmorg-18.1.8.zip"
        zip_path = llvm_dir.parent / zip_filename

        logger.info("Downloading LLVM source...")
        sp.run(
            [
                "wget",
                "https://github.com/llvm/llvm-project/archive/refs/tags/llvmorg-18.1.8.zip",
                "-O",
                str(zip_path),
            ],
            cwd=llvm_dir.parent,
            check=True,
        )

        logger.info("Extracting LLVM source...")
        # Extract the zip file - this creates llvm-project-llvmorg-18.1.8/
        sp.run(["unzip", str(zip_path)], cwd=llvm_dir.parent, check=True)

        # Rename the extracted directory to the desired llvm_dir name
        extracted_dir = llvm_dir.parent / "llvm-project-llvmorg-18.1.8"
        if extracted_dir.exists():
            extracted_dir.rename(llvm_dir)

        # Delete the zip file
        logger.info("Cleaning up zip file...")
        zip_path.unlink()

    llvm_abs_dir = llvm_dir.resolve()

    # Prepare the plugin files
    logger.info("Copying plugin files...")
    # cp llvm_utils/create_plugin.py $LLVM_DIR/clang/lib/Analysis/plugins/
    sp.run(
        [
            "cp",
            "llvm_utils/create_plugin.py",
            f"{llvm_abs_dir}/clang/lib/Analysis/plugins/",
        ]
    )
    plugin_work_dir = llvm_dir / "clang" / "lib" / "Analysis" / "plugins"
    # python3 ./create_plugin.py SAGenTest
    sp.run(["python3", "create_plugin.py", "SAGenTest"], cwd=plugin_work_dir.absolute())

    # Prepare utility functions
    logger.info("Copying utility functions...")
    # cp llvm_utils/utility.cpp $LLVM_DIR/clang/lib/StaticAnalyzer/Checkers/
    # cp llvm_utils/utility.h $LLVM_DIR/clang/include/clang/StaticAnalyzer/Checkers/
    sp.run(
        [
            "cp",
            "llvm_utils/utility.cpp",
            f"{llvm_abs_dir}/clang/lib/StaticAnalyzer/Checkers/",
        ]
    )
    sp.run(
        [
            "cp",
            "llvm_utils/utility.h",
            f"{llvm_abs_dir}/clang/include/clang/StaticAnalyzer/Checkers/",
        ]
    )

    cmakefile = (
        llvm_dir / "clang" / "lib" / "StaticAnalyzer" / "Checkers" / "CMakeLists.txt"
    )

    
    cmakefileold = f"{cmakefile}.old"
    os.rename(cmakefile, cmakefileold)

    # Add utility.cpp in right file at the right place
    with open(cmakefileold, 'r') as file:
        oldlines = file.readlines()

    # Open the file in write mode and write the modified lines back to it
    new_content = "utility.cpp"

    with open(cmakefile, 'w') as file:
        appended = False
        for line in oldlines:
            if not appended and line.strip().endswith(".cpp"):
                file.write("  " + new_content + "\n")
                appended = True
            file.write(line)

    file.close()
    os.remove(cmakefileold)


    # Build the LLVM
    logger.info("Building LLVM...")
    # mkdir -p $LLVM_DIR/build
    build_dir = llvm_dir / "build"
    # Delete the build directory if it exists
    if build_dir.exists():
        sp.run(["rm", "-rf", build_dir])
    build_dir.mkdir()

    # cmake
    # cmake -DLLVM_ENABLE_PROJECTS="clang;lld" -DLLVM_TARGETS_TO_BUILD=X86 -DCMAKE_BUILD_TYPE=Release -G "Unix Makefiles" ../llvm
    res = sp.run(
        'cmake -DLLVM_ENABLE_PROJECTS="clang;lld" -DLLVM_TARGETS_TO_BUILD=X86 -DCMAKE_BUILD_TYPE=Release -G "Unix Makefiles" ../llvm',
        cwd=build_dir,
        shell=True,
    )
    if res.returncode != 0:
        logger.error("CMake failed.")
        return

    # make
    make_res = sp.run("make -j32", cwd=build_dir, shell=True)
    if make_res.returncode != 0:
        logger.error("Make failed.")
        return

    make_res = sp.run("make SAGenTestPlugin -j32", cwd=build_dir, shell=True)
    if make_res.returncode != 0:
        logger.error("Make failed.")
        return
    logger.success("LLVM setup completed.")


if __name__ == "__main__":
    Fire(setup_llvm)
