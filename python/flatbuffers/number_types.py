# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from . import packer


# For reference, see:
# https://docs.python.org/2/library/ctypes.html#ctypes-fundamental-data-types-2

# These classes could be collections.namedtuple instances, but those are new
# in 2.6 and we want to work towards 2.5 compatability.

class TypeFlags(object):

    def __init__(self, bytewidth, min_val, max_val, py_type, name, packer_type):
        self.bytewidth = bytewidth
        self.min_val = min_val
        self.max_val = max_val
        self.py_type = py_type
        self.name = name
        self.packer_type = packer_type

    def __call__(self, n):
        return self.py_type(n)

    def valid_number(self, n):
        if self.min_val is None and self.max_val is None:
            return True
        return self.min_val <= n <= self.max_val

    def enforce_number(self, n):
        if self.min_val is None and self.max_val is None:
            return
        if not self.min_val <= n <= self.max_val:
            raise TypeError("bad number %s for type %s" % (str(n), self.name))


BoolFlags = TypeFlags(1, False, True, bool, "bool", packer.boolean)

Uint8Flags = TypeFlags(1, 0, (2**8) - 1, int, "uint8", packer.uint8)
Uint16Flags = TypeFlags(2, 0, (2**16) - 1, int, "uint16", packer.uint16)
Uint32Flags = TypeFlags(4, 0, (2**32) - 1, int, "uint32", packer.uint32)
Uint64Flags = TypeFlags(8, 0, (2**64) - 1, int, "uint64", packer.uint64)

Int8Flags = TypeFlags(1, -(2**7), (2**7) - 1, int, "int8", packer.int8)
Int16Flags = TypeFlags(2, -(2**15), (2**15) - 1, int, "int16", packer.int16)
Int32Flags = TypeFlags(4, -(2**31), (2**31) - 1, int, "int32", packer.int32)
Int64Flags = TypeFlags(8, -(2**63), (2**63) - 1, int, "int64", packer.int64)

Float32Flags = TypeFlags(4, -3.40282347e+38, 3.40282347e+38, float, "float32", packer.float32)
Float64Flags = TypeFlags(8, -1.7976931348623157e+308, 1.7976931348623157e+308, float, "float64", packer.float64)

SOffsetTFlags = Int32Flags
UOffsetTFlags = Uint32Flags
VOffsetTFlags = Uint16Flags


def float32_to_uint32(n):
    packed = packer.float32.pack(n)
    return packer.uint32.unpack(packed)[0]


def uint32_to_float32(n):
    packed = packer.uint32.pack(n)
    return packer.float32.unpack(packed)[0]


def float64_to_uint64(n):
    packed = packer.float64.pack(n)
    return packer.uint64.unpack(packed)[0]


def uint64_to_float64(n):
    packed = packer.uint64.pack(n)
    return packer.float64.unpack(packed)[0]
