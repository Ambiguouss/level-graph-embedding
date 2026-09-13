from setuptools import setup, Extension
from pybind11.setup_helpers import Pybind11Extension, build_ext
 
ext_modules = [
    Pybind11Extension(
        "graphcore",
        ["bindings.cpp"],
        cxx_std=17,
    ),
]
 
setup(
    name="graphcore",
    version="0.1.0",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    install_requires=["PySide6"],
)
 
