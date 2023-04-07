from dataclasses import dataclass

@dataclass
class Track:
    name: str
    slot: int
    ctype: int = 1

UNRELEASED_TRACKS = {
    "7e293e74991b0bf33e2ffa420b2ebe735ed23c38": Track("Six King Labyrinth", 44),
    "d54f59c8b3acf5db6fede98e3c7fd5800aac60eb": Track("Sea Stadium", 32),
    "4f86672b7014baf1f496e36ecf0c55ac455bf329": Track("Star Slope", 21),
    "e39dd5b4fbbf9793c291ecfae5443c804b1dfc60": Track("SNES Mario Circuit 1 v1", 81),
    "a8c1bf56c551246a128a7a3dcd3a8864ceda32e4": Track("Jungle Jamble", 61),
    "e1c46a6648a7651e04cafff63ca0dee2be160464": Track("GP Mario Beach v2", 74)
}
