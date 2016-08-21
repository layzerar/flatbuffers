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

from . import encode
from .number_types import (
    BoolFlags,
    Uint8Flags,
    Uint16Flags,
    Uint32Flags,
    Uint64Flags,
    Int8Flags,
    Int16Flags,
    Int32Flags,
    Int64Flags,
    Float32Flags,
    Float64Flags,
    SOffsetTFlags,
    UOffsetTFlags,
    VOffsetTFlags)


class Table(object):

    """Table wraps a byte slice and provides read access to its data.

    The variable `Pos` indicates the root of the FlatBuffers object therein."""

    __slots__ = ("Bytes", "Pos")

    def __init__(self, buf, pos):
        UOffsetTFlags.enforce_number(pos)

        self.Bytes = buf
        self.Pos = pos

    @classmethod
    def GetRoot(cls, buf, offset):
        """GetRoot retrieves the root object contained in the `buffer`."""
        n = encode.Get(UOffsetTFlags.packer_type, buf, offset)
        return cls(buf, n + offset)

    def Offset(self, vtableOffset):
        """
        Offset provides access into the Table's vtable. Deprecated fields
        are ignored by checking the vtable's length.
        """

        vtable = self.Pos - encode.Get(SOffsetTFlags.packer_type,
                                       self.Bytes,
                                       self.Pos)
        vtableEnd = encode.Get(VOffsetTFlags.packer_type, self.Bytes, vtable)
        if vtableOffset < vtableEnd:
            return encode.Get(VOffsetTFlags.packer_type,
                              self.Bytes,
                              vtable + vtableOffset)
        return 0

    def Indirect(self, off):
        """Indirect retrieves the relative offset stored at `offset`."""
        return off + self.Get(UOffsetTFlags, off)

    def String(self, off):
        """String gets a string from data stored inside the flatbuffer."""

        off += self.Get(UOffsetTFlags, off)
        length = self.Get(UOffsetTFlags, off)
        start = self.Pos + off + UOffsetTFlags.bytewidth
        return bytes(self.Bytes[start:start + length])

    def VectorLen(self, off):
        """
        VectorLen retrieves the length of the vector whose offset is stored
        at "off" in this object.
        """

        off += self.Get(UOffsetTFlags, off)
        ret = self.Get(UOffsetTFlags, off)
        return ret

    def Vector(self, off):
        """
        Vector retrieves the start of data of the vector whose offset is
        stored at "off" in this object.
        """

        x = off + self.Get(UOffsetTFlags, off)
        # data starts after metadata containing the vector length
        x += UOffsetTFlags.bytewidth
        return x

    def Union(self, off):
        """
        Union initializes any Table-derived type to point to the union at
        the given offset.
        """

        off += self.Get(UOffsetTFlags, off)
        return Table(self.Bytes, self.Pos + off)

    def Get(self, flags, off):
        """
        Get retrieves a value of the type specified by `flags`  at the
        given offset.
        """
        
        off += self.Pos
        return encode.Get(flags.packer_type, self.Bytes, off)

    def GetBool(self, off):
        return self.Get(BoolFlags, off)

    def GetByte(self, off):
        return self.Get(Uint8Flags, off)

    def GetUint8(self, off):
        return self.Get(Uint8Flags, off)

    def GetUint16(self, off):
        return self.Get(Uint16Flags, off)

    def GetUint32(self, off):
        return self.Get(Uint32Flags, off)

    def GetUint64(self, off):
        return self.Get(Uint64Flags, off)

    def GetInt8(self, off):
        return self.Get(Int8Flags, off)

    def GetInt16(self, off):
        return self.Get(Int16Flags, off)

    def GetInt32(self, off):
        return self.Get(Int32Flags, off)

    def GetInt64(self, off):
        return self.Get(Int64Flags, off)

    def GetFloat32(self, off):
        return self.Get(Float32Flags, off)

    def GetFloat64(self, off):
        return self.Get(Float64Flags, off)

    def GetUOffsetT(self, off):
        return self.Get(UOffsetTFlags, off)

    def GetVOffsetT(self, off):
        return self.Get(VOffsetTFlags, off)

    def GetSOffsetT(self, off):
        return self.Get(SOffsetTFlags, off)

    def GetSlot(self, flags, slot, d):
        off = self.Offset(slot)
        if off == 0:
            return d
        return self.Get(flags, off)

    def GetBoolSlot(self, slot, d):
        return self.GetSlot(BoolFlags, slot, d)

    def GetByteSlot(self, slot, d):
        return self.GetSlot(Uint8Flags, slot, d)

    def GetUint8Slot(self, slot, d):
        return self.GetSlot(Uint8Flags, slot, d)

    def GetUint16Slot(self, slot, d):
        return self.GetSlot(Uint16Flags, slot, d)

    def GetUint32Slot(self, slot, d):
        return self.GetSlot(Uint32Flags, slot, d)

    def GetUint64Slot(self, slot, d):
        return self.GetSlot(Uint64Flags, slot, d)

    def GetInt8Slot(self, slot, d):
        return self.GetSlot(Int8Flags, slot, d)

    def GetInt16Slot(self, slot, d):
        return self.GetSlot(Int16Flags, slot, d)

    def GetInt32Slot(self, slot, d):
        return self.GetSlot(Int32Flags, slot, d)

    def GetInt64Slot(self, slot, d):
        return self.GetSlot(Int64Flags, slot, d)

    def GetFloat32Slot(self, slot, d):
        return self.GetSlot(Float32Flags, slot, d)

    def GetFloat64Slot(self, slot, d):
        return self.GetSlot(Float64Flags, slot, d)

    def GetVOffsetTSlot(self, slot, d):
        """
        GetVOffsetTSlot retrieves the VOffsetT that the given vtable location
        points to. If the vtable value is zero, the default value `d`
        will be returned.
        """
        off = self.Offset(slot)
        if off == 0:
            return d
        return off
