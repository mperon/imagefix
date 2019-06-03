#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import os
import platform
import pprint
import re
import time
from datetime import datetime
from pathlib import Path

import piexif
from PIL import ExifTags, Image

main_dir = "/home/marcos/Downloads/Fotos"
new_dir = "/home/marcos/Downloads/Fotos_New"
ACCEPTABLE_EXTENSIONS = (".jpg", ".jpeg",)


def main():
    Path(new_dir).mkdir(parents=True, exist_ok=True)
    walk(Path(main_dir))


def walk(directory):
    for f in directory.iterdir():
        if f.is_file():
            if str(f).lower().endswith(ACCEPTABLE_EXTENSIONS):
                process_file(f)
        else:
            walk(f)


def process_file(f):
    with Image.open(f) as img:
        exif_dict = piexif.load(img.info['exif'])
        # new_dict = {}
        # new_dict["DateTime"] = read_exif_tag(
        #     exif_dict, "0th", piexif.ImageIFD.DateTime, as_string=True)
        # new_dict["DateTimeOriginal"] = read_exif_tag(
        #     exif_dict, "0th", piexif.ExifIFD.DateTimeOriginal, as_string=True)
        # new_dict["DateTimeDigitized"] = read_exif_tag(
        #     exif_dict, "0th", piexif.ExifIFD.DateTimeDigitized, as_string=True)

        # new_dict["GPSDateTime"] = get_gps_datetime(exif_dict)
        # set comment
        set_exif_tag(exif_dict, "Exif", piexif.ExifIFD.UserComment,
                     "testando".encode("utf-8"))
        new_file = prepare_path(f, new_dir)
        exif_bytes = piexif.dump(exif_dict)
        print("File: {}".format(new_file))
        img.save(new_file, "jpeg", exif=exif_bytes,
                 quality="keep", optimize=True)


def get_gps_datetime(exif_dict):
    b_gpsdate = read_exif_tag(exif_dict, "GPS", piexif.GPSIFD.GPSDateStamp)
    t_gpstime = read_exif_tag(exif_dict, "GPS", piexif.GPSIFD.GPSTimeStamp)
    b_gpsdate = b_gpsdate.decode() if isinstance(b_gpsdate, bytes) else b_gpsdate
    if isinstance(b_gpsdate, str):
        # Change date colon to dash
        gpsd = b_gpsdate.replace('-/\\', ':')
        if isinstance(t_gpstime, tuple):
            gpst = ':'.join(map('{0:0>2}'.format,  # Convert tuple to padded zero str
                                (t_gpstime[0][0], t_gpstime[1][0], t_gpstime[2][0])))
        else:
            gpst = '00:00:00'
        return gpsd + ' ' + gpst
    return None


def set_exif_tag(exif_dict, etype, key, value):
    if not etype in exif_dict:
        exif_dict[etype] = {}
    exif_dict[etype][key] = value


def read_exif_tag(exif_dict, etype, key, as_string=False):
    if etype in exif_dict:
        if key in exif_dict[etype]:
            result = exif_dict[etype][key]
            if as_string:
                return result.decode("utf-8")
            return result
    return None


def prepare_path(f, new_dir):
    relative_path = Path(f).relative_to(main_dir)
    new_path = Path(new_dir).joinpath(relative_path)
    Path(new_path).parent.mkdir(parents=True, exist_ok=True)
    return new_path


if __name__ == "__main__":
    main()
