import lzma
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from io import BytesIO, IOBase
from pathlib import Path
from shutil import rmtree
from typing import Callable, Generator

import requests
from PIL import Image
from sh import mount, umount  # type: ignore
from sh.contrib import sudo  # type: ignore

from TrackPacks_pb2 import AliasDB, Pack, ProtoSha1, ProtoTrack
from unreleased_tracks import UNRELEASED_TRACKS


@dataclass
class PackInfo:
    name: str
    author: str
    description: str

    course_folder: Path
    preprocess: Callable[[], None]
    cleanup: Callable[[], None]

CTGP = Path("ctgp")
OUT = Path("./out")
IN = Path("./in")

CTGP_TRACKS = CTGP / "PACKAGES" / "CTGPR" / "RACE" / "COURSE"

TRACKS = OUT / "tracks"
THUMBNAILS = OUT / "thumbnails"
TEMP_TRACKS = OUT / "temp tracks"
UNKNOWN_TRACKS = OUT / "unknown tracks"

def glob_multi(folder: Path, *patterns: str) -> Generator[Path, None, None]:
    for pat in patterns:
        yield from folder.glob(pat)

def process_thumbnail(sha1: str, raw: IOBase):
    image = Image.open(raw)
    image = image.resize((256, 144))
    image.save(THUMBNAILS / f"{sha1}.jpg")

def find_track_id(alias_db: AliasDB, proto_sha1: ProtoSha1) -> tuple[ProtoSha1, ProtoTrack] | None:
    try:
        sha1 = proto_sha1.data.hex()
        with open(f"in/tracks/{sha1}.pb.bin", "rb") as track_file:
            track = ProtoTrack()
            track.ParseFromString(track_file.read())

            return (proto_sha1, track)
    except FileNotFoundError:
        for alias_value in alias_db.aliases:
            if alias_value.aliased == proto_sha1:
                track = find_track_id(alias_db, alias_value.real)
                return track

def fetch_thumbnail(track_id: str, sha1: str):
    track_id = track_id.rjust(5, "0")
    if (THUMBNAILS / f"{track_id}.jpg").exists():
        return

    resp = requests.get(f"http://archive.tock.eu/fullpreview/{track_id[-2:]}/{track_id}.jpg")
    if resp.status_code == 404:
        backup_thumbnail = Path(f"thumbnails/{sha1}.png")
        if not backup_thumbnail.exists():
            return

        with open(backup_thumbnail, "rb") as f:
            resp_bytes = f.read()
    else:
        resp.raise_for_status()
        resp_bytes = resp.content

    process_thumbnail(sha1, BytesIO(resp_bytes))

def recompress_track(track_path: Path, proto_sha1: ProtoSha1, track: ProtoTrack):
    sha1 = proto_sha1.data.hex()
    subprocess.run(["wszst", "decompress", "--norm", "--u8", track_path, "-d", TEMP_TRACKS / f"{sha1}.u8"])

    u8_file = TEMP_TRACKS / f"{sha1}.u8"
    meta_file = TRACKS / f"{sha1}.pb.bin"
    lzma_file = TRACKS / f"{sha1}.arc.lzma"
    with open(u8_file, "rb") as f:
        with lzma.open(lzma_file, "wb", format=lzma.FORMAT_ALONE) as g:
            print(f"RECOMPRESS U8:{u8_file} -> {lzma_file}")
            g.write(f.read())

    with open(meta_file, "wb") as meta:
        meta.write(track.SerializeToString())

def ctgp_extract():
    if not Path(OUT / "blob.dat").exists():
        import decrypter

        decrypter.run(
            open(IN / "blob.bin", "rb"),
            open(OUT / "blob.dat", "wb"),
            encode=False
        )

    CTGP.mkdir(exist_ok=True)
    mount(OUT / "blob.dat", CTGP)

def ctgp_cleanup():
    if CTGP.exists():
        umount(CTGP)
        rmtree(CTGP)


def identity(): ...

PACKS = {
    "CTGP": PackInfo("Custom Track Grand Prix", "Mr Bean35000vr & Chadderz", "A custom track pack for Mario Kart Wii", CTGP_TRACKS, ctgp_extract, ctgp_cleanup),
    "MKW-DX": PackInfo("Mario Kart Wii Deluxe", "FJRoyet", "A custom track pack for Mario Kart Wii", IN / "Course", identity, identity),
    "MIDNIGHT": PackInfo("Mario Kart Midnight", "marionose1, ZPL, and Demonz", "A celebration of custom tracks, featuring the \"best\" tracks released between December 2021 and November 2022.", IN / "midnight", identity, identity),
}


def main(pack: PackInfo, pool: ProcessPoolExecutor):
    for folder in (TRACKS, TEMP_TRACKS, UNKNOWN_TRACKS):
        rmtree(folder, ignore_errors=True)

    for folder in (OUT, TRACKS, THUMBNAILS, TEMP_TRACKS, UNKNOWN_TRACKS):
        folder.mkdir(exist_ok=True)

    pack.preprocess()

    with open("in/alias.pb.bin", "rb") as alias_file:
        alias_db = AliasDB()
        alias_db.ParseFromString(alias_file.read())

    race_tracks: list[ProtoSha1] = []
    battle_tracks: list[ProtoSha1] = []
    for track_path in glob_multi(pack.course_folder, "*.SZS", "*.szs"):
        sha1 = subprocess.run(["wszst", "sha1", "--norm", track_path], capture_output=True).stdout.decode().split(" ")[0]
        if sha1 == "d52d50bf4c8aa6a48dfbc361e642b1d314a2ff6d":
            # CTGP has empty track files...
            continue

        proto_sha1 = ProtoSha1(data=bytes.fromhex(sha1))
        track_info = find_track_id(alias_db, proto_sha1)

        track: ProtoTrack
        if track_info is not None:
            proto_sha1, track = track_info
            sha1 = proto_sha1.data.hex()
            is_battle = track.type == 2

            pool.submit(fetch_thumbnail, str(track.wiimmId), sha1)
        elif (unreleased_info := UNRELEASED_TRACKS.get(sha1)) is not None:
            is_battle = unreleased_info.ctype == 2
            track = ProtoTrack (
                name=unreleased_info.name,
                slotId=unreleased_info.slot,
                type=unreleased_info.ctype,
            )

            try:
                with open(f"thumbnails/{sha1}.png", "rb") as f:
                    raw = f.read()
            except FileNotFoundError:
                print(f"Warning: Could not find thumbnail for {sha1}")
            else:
                process_thumbnail(sha1, BytesIO(raw))
        else:
            print(f"!!! Could not find information for {track_path.stem} ({sha1}) !!!")
            shutil.copyfile(track_path, UNKNOWN_TRACKS / track_path.name)
            continue

        track_list = battle_tracks if is_battle else race_tracks
        if proto_sha1 not in track_list:
            track_list.append(proto_sha1)
            pool.submit(recompress_track, track_path, proto_sha1, track)
        else:
            print(f"!!! Duplicate track {track_path.stem} ({sha1}) !!!)")

    with open(OUT / "manifest.pb.bin", "wb") as f:
        f.write(Pack(
            name=pack.name,
            authorNames=pack.author,
            description=pack.description,
            raceTracks=race_tracks,
            coinTracks=battle_tracks,
            balloonTracks=battle_tracks,
        ).SerializeToString())

if __name__ == "__main__":
    pack = PACKS[input("Pack: ")]

    with sudo:
        try:
            with ProcessPoolExecutor() as pool:
                main(pack, pool)
        finally:
            pack.cleanup()
