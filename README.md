# Automatic Track Pack Generator
This python script will decrypt, mount, and extract tracks from existing Mario Kart Wii
custom track distributions, and produce `out/tracks`, `out/thumbnails`, and `out/manifest.pb.bin` to be used in [MKW-SP](https://github.com/GnomedDev/mkw-sp/tree/track-packs-new).

**This script is currently under heavy development and at time of publishing
there is not support for loading these files in upstream MKW-SP.**

## How to run?

A base requirement is a `tracks` folder from [`wiimm-db-parser`](https://github.com/GnomedDev/mkw-sp/tree/track-packs-new/tools/wiimm-db-parser) in the `in` directory.

1. Get yourself on a sane distribution of Linux.
2. Install `requests`, `pillow`, and `sh` with PIP.
3. Follow the below instructions to setup your pack.
4. Run `main.py`.

# Supported Packs
## CTGP

Place the `blob.bin` from the `ctgpr` directory on your SD card into the `in` folder.

This will be decrypted into the `out/blob.dat` file, then mounted in the `ctgp` folder while the script is running. 99% of tracks work, but there are a couple missing or invalid tracks.

## Mario Kart Wii Deluxe *(Unfinished)*
Place `mkwdx/Course` in the `in` folder.

This pack has a lot of semi-edited tracks, so either a reliable source needs to be found to parse from, or `unreleased_tracks.py` needs to be filled in with a lot of entries.

# Credits
- Thanks to the original Pack creators and track authors, for the contributions to the community.
- Thanks to [Palapeli](https://github.com/mkwcat) for the original source of `decrypter.py`.
- Thanks to Tock for the [thumbnail source](http://archive.tock.eu).
