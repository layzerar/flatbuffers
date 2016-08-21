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

from . import encode
from . import packer

from .compat import (
    range_func,
    memoryview_type,
    string_types,
    binary_type)
from .exceptions import (
    OffsetArithmeticError,
    NotInObjectError,
    ObjectIsNestedError,
    StructIsNotInlineError,
    BuilderSizeError)


# VtableMetadataFields is the count of metadata fields in each vtable.
VtableMetadataFields = 2


class Builder(object):

    """
    A Builder is used to construct one or more FlatBuffers. Typically, Builder
    objects will be used from code generated by the `flatc` compiler.

    A Builder constructs byte buffers in a last-first manner for simplicity and
    performance during reading.

    Internally, a Builder is a state machine for creating FlatBuffer objects.

    It holds the following internal state:
        Bytes: an array of bytes.
        current_vtable: a list of integers.
        vtables: a list of vtable entries (i.e. a list of list of integers).
    """

    __slots__ = ("Bytes", "current_vtable", "head", "minalign", "objectEnd",
                 "vtables")

    """
    Maximum buffer size constant, in bytes.
    Builder will never allow it's buffer grow over this size.
    Currently equals 2Gb.
    """
    MAX_BUFFER_SIZE = 2**31

    def __init__(self, initialSize=1024):
        """
        Initializes a Builder of size `initial_size`.
        The internal buffer is grown as needed.
        """

        if not (0 <= initialSize <= Builder.MAX_BUFFER_SIZE):
            msg = "flatbuffers: Cannot create Builder larger than 2 gigabytes."
            raise BuilderSizeError(msg)

        self.Bytes = bytearray(initialSize)
        self.current_vtable = None
        self.head = len(self.Bytes)
        self.minalign = 1
        self.objectEnd = None
        self.vtables = []

    def Output(self):
        """
        Output returns the portion of the buffer that has been used for
        writing data.
        """

        return bytes(self.Bytes[self.head:])

    def Reset(self):
        """
        Reset truncates the underlying Builder buffer, facilitating alloc-free
        reuse of a Builder. It also resets bookkeeping data.
        """

        self.vtables = []
        self.current_vtable = None
        self.head = len(self.Bytes)
        self.minalign = 1
        self.objectEnd = None

    def StartObject(self, numfields):
        """StartObject initializes bookkeeping for writing a new object."""

        self.assertNotNested()

        # use 32-bit offsets so that arithmetic doesn't overflow.
        self.current_vtable = [0] * numfields
        self.objectEnd = self.Offset()
        self.minalign = 1

    def WriteVtable(self):
        """
        WriteVtable serializes the vtable for the current object, if needed.

        Before writing out the vtable, this checks pre-existing vtables for
        equality to this one. If an equal vtable is found, point the object to
        the existing vtable and return.

        Because vtable values are sensitive to alignment of object data, not
        all logically-equal vtables will be deduplicated.

        A vtable has the following format:
          <VOffsetT: size of the vtable in bytes, including this value>
          <VOffsetT: size of the object in bytes, including the vtable offset>
          <VOffsetT: offset for a field> * N, where N is the number of fields
                     in the schema for this type. Includes deprecated fields.
        Thus, a vtable is made of 2 + N elements, each VOffsetT bytes wide.

        An object has the following format:
          <SOffsetT: offset to this object's vtable (may be negative)>
          <byte: data>+
        """

        # Prepend a zero scalar to the object. Later in this function we'll
        # write an offset here that points to the object's vtable:
        self.PrependSOffsetTRelative(0)

        objectOffset = self.Offset()
        existingVtable = None

        # Search backwards through existing vtables, because similar vtables
        # are likely to have been recently appended. See
        # BenchmarkVtableDeduplication for a case in which this heuristic
        # saves about 30% of the time used in writing objects with duplicate
        # tables.

        for vt2Offset in reversed(self.vtables):
            # Find the other vtable, which is associated with `i`:
            vt2Start = len(self.Bytes) - vt2Offset
            vt2Len = encode.Get(packer.voffset, self.Bytes, vt2Start)

            metadata = VtableMetadataFields * VOffsetTFlags.bytewidth
            vt2End = vt2Start + vt2Len
            vt2 = memoryview_type(self.Bytes)[vt2Start + metadata:vt2End]

            # Compare the other vtable to the one under consideration.
            # If they are equal, store the offset and break:
            if vtableEqual(self.current_vtable, objectOffset, vt2):
                existingVtable = vt2Offset
                break

        if existingVtable is None:
            # Did not find a vtable, so write this one to the buffer.

            # Write out the current vtable in reverse , because
            # serialization occurs in last-first order:
            for off in reversed(self.current_vtable):
                if off != 0:
                    # Forward reference to field;
                    # use 32bit number to ensure no overflow:
                    off = objectOffset - off
                self.PrependVOffsetT(off)

            # The two metadata fields are written last.

            # First, store the object bytesize:
            self.PrependVOffsetT(objectOffset - self.objectEnd)

            # Second, store the vtable bytesize:
            vBytes = len(self.current_vtable) + VtableMetadataFields
            vBytes *= VOffsetTFlags.bytewidth
            self.PrependVOffsetT(vBytes)

            # Next, write the offset to the new vtable in the
            # already-allocated SOffsetT at the beginning of this object:
            encode.Write(packer.soffset,
                         self.Bytes,
                         len(self.Bytes) - objectOffset,
                         self.Offset() - objectOffset)

            # Finally, store this vtable in memory for future
            # deduplication:
            self.vtables.append(self.Offset())
        else:
            # Found a duplicate vtable.
            self.head = len(self.Bytes) - objectOffset

            # Write the offset to the found vtable in the
            # already-allocated SOffsetT at the beginning of this object:
            encode.Write(packer.soffset, self.Bytes, self.head,
                         existingVtable - objectOffset)

        self.current_vtable = None
        return objectOffset

    def EndObject(self):
        """EndObject writes data necessary to finish object construction."""
        if self.current_vtable is None:
            msg = ("flatbuffers: Tried to write the end of an Object when "
                   "the Builder was not currently writing an Object.")
            raise NotInObjectError(msg)
        return self.WriteVtable()

    def growByteBuffer(self, freeSize):
        """Doubles the size of the byteslice, and copies the old data towards
           the end of the new buffer (since we build the buffer backwards)."""
        oldSize = len(self.Bytes)
        newSize = max(1024, oldSize * 2, oldSize + freeSize - self.head)
        if newSize >= self.MAX_BUFFER_SIZE:
            msg = "flatbuffers: cannot grow buffer beyond 2 gigabytes"
            raise BuilderSizeError(msg)

        newBytes = bytearray(newSize)
        newBytes[newSize - oldSize:] = self.Bytes
        self.Bytes = newBytes
        self.head += newSize - oldSize

    def Head(self):
        """
        Head gives the start of useful data in the underlying byte buffer.
        Note: unlike other functions, this value is interpreted as from the left.
        """
        return self.head

    def Offset(self):
        """Offset relative to the end of the buffer."""
        return len(self.Bytes) - self.head

    def Pad(self, n):
        """Pad places zeros at the current offset."""
        for index in range_func(self.head - n, self.head):
            self.Bytes[index] = 0
        self.head -= n

    def Prep(self, size, additionalBytes):
        """
        Prep prepares to write an element of `size` after `additional_bytes`
        have been written, e.g. if you write a string, you need to align
        such the int length field is aligned to SizeInt32, and the string
        data follows it directly.
        If all you need to do is align, `additionalBytes` will be 0.
        """

        # Track the biggest thing we've ever aligned to.
        if size > self.minalign:
            self.minalign = size

        # Find the amount of alignment needed such that `size` is properly
        # aligned after `additionalBytes`:
        alignSize = (~(len(self.Bytes) - self.head + additionalBytes)) + 1
        alignSize &= (size - 1)
        totalSize = alignSize + size + additionalBytes

        # Reallocate the buffer if needed:
        if self.head < totalSize:
            self.growByteBuffer(totalSize)
        self.head -= alignSize

    def PrependSOffsetTRelative(self, off):
        """
        PrependSOffsetTRelative prepends an SOffsetT, relative to where it
        will be written.
        """

        # Ensure alignment is already done:
        self.Prep(SOffsetTFlags.bytewidth, 0)
        off2 = self.Offset() - off
        if not (off2 >= 0):
            msg = "flatbuffers: Offset arithmetic error."
            raise OffsetArithmeticError(msg)
        self.Place(off2 + SOffsetTFlags.bytewidth, SOffsetTFlags)

    def PrependUOffsetTRelative(self, off):
        """
        PrependUOffsetTRelative prepends an UOffsetT, relative to where it
        will be written.
        """

        # Ensure alignment is already done:
        self.Prep(UOffsetTFlags.bytewidth, 0)
        off2 = self.Offset() - off
        if not (off2 >= 0):
            msg = "flatbuffers: Offset arithmetic error."
            raise OffsetArithmeticError(msg)
        self.Place(off2 + UOffsetTFlags.bytewidth, UOffsetTFlags)

    def StartVector(self, elemSize, numElems, alignment):
        """
        StartVector initializes bookkeeping for writing a new vector.

        A vector has the following format:
          <UOffsetT: number of elements in this vector>
          <T: data>+, where T is the type of elements of this vector.
        """

        self.assertNotNested()
        self.Prep(Uint32Flags.bytewidth, elemSize * numElems)
        self.Prep(alignment, elemSize * numElems)  # In case alignment > int.
        return self.Offset()

    def EndVector(self, vectorNumElems):
        """EndVector writes data necessary to finish vector construction."""

        # we already made space for this, so write without PrependUint32
        self.Place(vectorNumElems, UOffsetTFlags)
        return self.Offset()

    def CreateString(self, s):
        """CreateString writes a null-terminated byte string as a vector."""

        self.assertNotNested()

        if isinstance(s, string_types):
            x = s.encode()
        elif isinstance(s, binary_type):
            x = s
        else:
            raise TypeError("non-string passed to CreateString")

        l = len(x)
        self.Prep(UOffsetTFlags.bytewidth, l + 1)
        self.Pad(1)

        self.head -= l
        self.Bytes[self.head:self.head + l] = x

        return self.EndVector(l)

    def assertNotNested(self):
        """
        Check that no other objects are being built while making this
        object. If not, raise an exception.
        """

        if self.current_vtable is not None:
            msg = ("flatbuffers: Tried to write a new Object when the "
                   "Builder was already writing an Object.")
            raise ObjectIsNestedError(msg)

    def assertNested(self, obj):
        """
        Structs are always stored inline, so need to be created right
        where they are used. You'll get this error if you created it
        elsewhere.
        """

        if obj != self.Offset():
            msg = ("flatbuffers: Tried to write a Struct at an Offset that "
                   "is different from the current Offset of the Builder.")
            raise StructIsNotInlineError(msg)

    def Slot(self, slotnum):
        """
        Slot sets the vtable key `voffset` to the current location in the
        buffer.

        """
        if self.current_vtable is None:
            msg = ("flatbuffers: Tried to write an Object field when "
                   "the Builder was not currently writing an Object.")
            raise NotInObjectError(msg)

        self.current_vtable[slotnum] = self.Offset()

    def Finish(self, rootTable):
        """Finish finalizes a buffer, pointing to the given `rootTable`."""
        self.Prep(self.minalign, UOffsetTFlags.bytewidth)
        self.PrependUOffsetTRelative(rootTable)
        return self.head

    def Prepend(self, flags, off):
        self.Prep(flags.bytewidth, 0)
        self.Place(off, flags)

    def PrependBool(self, x):
        self.Prep(BoolFlags.bytewidth, 0)
        self.PlaceBool(x)

    def PrependByte(self, x):
        self.Prep(Uint8Flags.bytewidth, 0)
        self.PlaceUint8(x)

    def PrependUint8(self, x):
        self.Prep(Uint8Flags.bytewidth, 0)
        self.PlaceUint8(x)

    def PrependUint16(self, x):
        self.Prepend(Uint16Flags, x)

    def PrependUint32(self, x):
        self.Prepend(Uint32Flags, x)

    def PrependUint64(self, x):
        self.Prepend(Uint64Flags, x)

    def PrependInt8(self, x):
        self.Prep(Int8Flags.bytewidth, 0)
        self.PlaceInt8(x)

    def PrependInt16(self, x):
        self.Prepend(Int16Flags, x)

    def PrependInt32(self, x):
        self.Prepend(Int32Flags, x)

    def PrependInt64(self, x):
        self.Prepend(Int64Flags, x)

    def PrependFloat32(self, x):
        self.Prepend(Float32Flags, x)

    def PrependFloat64(self, x):
        self.Prepend(Float64Flags, x)

    def PrependVOffsetT(self, x):
        self.Prepend(VOffsetTFlags, x)

    def PrependSlot(self, flags, o, x, d):
        if x != d:
            self.Prepend(flags, x)
            self.Slot(o)

    def PrependBoolSlot(self, o, x, d):
        if x != d:
            self.PrependBool(x)
            self.Slot(o)

    def PrependByteSlot(self, o, x, d):
        if x != d:
            self.PrependByte(x)
            self.Slot(o)

    def PrependUint8Slot(self, o, x, d):
        if x != d:
            self.PrependUint8(x)
            self.Slot(o)

    def PrependUint16Slot(self, o, x, d):
        self.PrependSlot(Uint16Flags, o, x, d)

    def PrependUint32Slot(self, o, x, d):
        self.PrependSlot(Uint32Flags, o, x, d)

    def PrependUint64Slot(self, o, x, d):
        self.PrependSlot(Uint64Flags, o, x, d)

    def PrependInt8Slot(self, o, x, d):
        if x != d:
            self.PrependInt8(x)
            self.Slot(o)

    def PrependInt16Slot(self, o, x, d):
        self.PrependSlot(Int16Flags, o, x, d)

    def PrependInt32Slot(self, o, x, d):
        self.PrependSlot(Int32Flags, o, x, d)

    def PrependInt64Slot(self, o, x, d):
        self.PrependSlot(Int64Flags, o, x, d)

    def PrependFloat32Slot(self, o, x, d):
        self.PrependSlot(Float32Flags, o, x, d)

    def PrependFloat64Slot(self, o, x, d):
        self.PrependSlot(Float64Flags, o, x, d)

    def PrependUOffsetTRelativeSlot(self, o, x, d):
        """
        PrependUOffsetTRelativeSlot prepends an UOffsetT onto the object at
        vtable slot `o`. If value `x` equals default `d`, then the slot will
        be set to zero and no other data will be written.
        """

        if x != d:
            self.PrependUOffsetTRelative(x)
            self.Slot(o)

    def PrependStructSlot(self, v, x, d):
        """
        PrependStructSlot prepends a struct onto the object at vtable slot `o`.
        Structs are stored inline, so nothing additional is being added.
        In generated code, `d` is always 0.
        """

        if x != d:
            self.assertNested(x)
            self.Slot(v)

    def Place(self, x, flags):
        """
        Place prepends a value specified by `flags` to the Builder,
        without checking for available space.
        """
        head = self.head - flags.bytewidth
        encode.Write(flags.packer_type, self.Bytes, head, x)
        self.head = head

    def PlaceBool(self, x):
        """
        Place prepends a Bool to the Builder,
        without checking for available space.
        """
        head = self.head - 1
        self.Bytes[head] = int(x)
        self.head = head

    def PlaceUint8(self, x):
        """
        Place prepends a Int8 to the Builder,
        without checking for available space.
        """
        head = self.head - 1
        self.Bytes[head] = x
        self.head = head

    def PlaceInt8(self, x):
        """
        Place prepends a Uint8 to the Builder,
        without checking for available space.
        """
        head = self.head - 1
        self.Bytes[head] = x & 0xff
        self.head = head


def vtableEqual(a, objectStart, b):
    """vtableEqual compares an unwritten vtable to a written vtable."""

    if len(a) * VOffsetTFlags.bytewidth != len(b):
        return False

    for i, elem in enumerate(a):
        x = encode.Get(packer.voffset, b, i * VOffsetTFlags.bytewidth)

        # Skip vtable entries that indicate a default value.
        if x == 0 and elem == 0:
            pass
        else:
            y = objectStart - elem
            if x != y:
                return False
    return True
