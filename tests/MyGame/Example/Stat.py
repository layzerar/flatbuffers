# automatically generated, do not modify

# namespace: Example

import flatbuffers

class Stat(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAsStat(cls, buf, offset):
        x = cls(flatbuffers.Table.GetRoot(buf, offset))
        return x


    # Stat
    def __init__(self, tab):
        self._tab = tab

    # Stat
    def Id(self):
        o = self._tab.Offset(4)
        if o != 0:
            return self._tab.String(o)
        return b""

    # Stat
    def Val(self):
        o = self._tab.Offset(6)
        if o != 0:
            return self._tab.GetInt64(o)
        return 0

    # Stat
    def Count(self):
        o = self._tab.Offset(8)
        if o != 0:
            return self._tab.GetUint16(o)
        return 0


def CreateStat(builder,
        id=None,
        val=None,
        count=None):
    builder.StartObject(3)
    if id is not None:
        builder.PrependUOffsetTRelativeSlot(0, id, 0)
    if val is not None:
        builder.PrependInt64Slot(1, val, 0)
    if count is not None:
        builder.PrependUint16Slot(2, count, 0)
    return builder.EndObject()

def StatStart(builder): builder.StartObject(3)
def StatAddId(builder, id): builder.PrependUOffsetTRelativeSlot(0, id, 0)
def StatAddVal(builder, val): builder.PrependInt64Slot(1, val, 0)
def StatAddCount(builder, count): builder.PrependUint16Slot(2, count, 0)
def StatEnd(builder): return builder.EndObject()
