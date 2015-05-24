# -*- coding: utf-8 -*-
import sys

from setuptools import setup
from setuptools import Extension

from Cython.Build import cythonize
from Cython.Distutils import build_ext


if sys.platform == "win32":
    extra_compile_args = ['/EHsc']
else:
    extra_compile_args = ['-std=c++11']


setup(
    name='flatbuffers',
    version='0.1',
    license='BSD',
    author='FlatBuffers Contributors',
    author_email='me@rwinslow.com',
    url='https://github.com/google/flatbuffers/python',
    long_description=('Python runtime library and code generator for use with'
                      'the Flatbuffers serialization format.'),
    packages=['flatbuffers'],
    ext_modules=[Extension(
        'flatbuffers.fastcodec',
        sources=['flatbuffers/fastcodec.pyx'],
        include_dirs=['../include'],
        extra_compile_args=extra_compile_args,
        language='c++',
    )],
    cmdclass={'build_ext': build_ext},
    include_package_data=True,
    requires=[],
    description=('Runtime library and code generator for use with the '
                 'Flatbuffers serialization format.'),
)
