from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext
import sys

# Maximum optimization flags: /O2 for Windows, -O3 for Linux/Mac
compile_args = ["/O2"] if sys.platform == "win32" else ["-O3"]

ext_modules = [
    Pybind11Extension(
        "pathfinder_core",
        ["src/graph.cpp"],
        extra_compile_args=compile_args,
    ),
]

setup(
    name="pathfinder_core",
    version="0.1",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)

