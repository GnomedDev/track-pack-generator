from dataclasses import dataclass

@dataclass
class Track:
    name: str
    slot: int
    ctype: int = 1

UNRELEASED_TRACKS = {
    # Fuck Torran
    "4f86672b7014baf1f496e36ecf0c55ac455bf329": Track("Star Slope", 21),
    "a8c1bf56c551246a128a7a3dcd3a8864ceda32e4": Track("Jungle Jamble", 61),

    # Removed GIFs
    "cd19d287b6578a396c8a4ec77acf0c633b5c75a8": Track("Disco Fever", 13),
}
