from typing import BinaryIO

class TrackEntry:
    def __init__(self, crs1: BinaryIO):
        self.course_name = crs1.read(0x80).strip(b"\x00").decode("ascii")
        self.file_name = crs1.read(0x40).strip(b"\x00\x05").decode("ascii")
        self.music_id = int.from_bytes(crs1.read(4), "big")
        self.slot_id = int.from_bytes(crs1.read(4), "big")
        crs1.read(4 * 14) # padding

def parse(crs1: BinaryIO) -> dict[str, TrackEntry]:
    assert crs1.read(4) == b"CRS1"
    crs1.read(4) # length
    assert crs1.read(4) == bytes([0, 0, 0, 0]) # version
    race_count = int.from_bytes(crs1.read(4), "big")
    battle_count = int.from_bytes(crs1.read(4), "big")

    # Unnessesary data + padding
    crs1.read((4 * 8) + (4 * 3))

    tracks = (TrackEntry(crs1) for _ in range(race_count))
    return {track.file_name: track for track in tracks}

if __name__ == "__main__":
    with open("CRS1.BIN", "rb") as crs1:
        print(parse(crs1))
