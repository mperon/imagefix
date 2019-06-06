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

main_dir = "D:\\Usuarios\\Peron\\Downloads\\COTE"
ACCEPTABLE_EXTENSIONS = (".jpg", ".jpeg",)


def main():
    processor = ImageProcessor()
    walk(Path(main_dir), processor)


def walk(directory, processor):
    for f in directory.iterdir():
        if f.is_file():
            if str(f).lower().endswith(ACCEPTABLE_EXTENSIONS):
                process_file(f, processor)
        else:
            walk(f, processor)


def process_file(file_obj, processor):
    img_obj = ImgObject(file_obj)
    processor.process(img_obj)


class ImgObject():
    def __init__(self, file_obj, img=None, dates=None):
        super().__init__()
        if isinstance(file_obj, str):
            self.file_obj = Path(file_obj)
        self.file_obj = file_obj
        if img is None:
            self.img = img
        if dates is None:
            self.dates = {}


class ImageProcessor():

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.date_finder = ImageDateFinder()
        self.date_chooser = ImageDateChooser()
        self.date_saver = ImageDateSaver()

    def process(self, img_obj):
        with Image.open(img_obj.file_obj) as img:
            img_obj.img = img
            img_obj.exif_data = piexif.load(img.info["exif"])
            # search dates
            self.date_finder.get_dates(img_obj)
            img_obj.choosen = self.date_chooser.choose(img_obj)
            # if img_obj.choosen:
            #     self.date_saver.write(img_obj)


class ImageDateSaver():
    EXIF_TAGS = [
        0x0132,
        0x9003,
        0x9004,
    ]

    EXIF_BACKUP_TAG = [
        0x010e
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def write(self, img_obj):
        self.backup_data(img_obj)
        self.write_exif(img_obj)
        # rename current file
        back_name = img_obj.file_obj.with_suffix('.old')
        img_obj.new_name = img_obj.file_obj.with_suffix('.jpg')
        os.rename(img_obj.file_obj, back_name)
        exif_bytes = piexif.dump(img_obj.exif_data)
        img_obj.img.save(img_obj.new_name, exif=exif_bytes)
        self.change_modtime(img_obj)

    def write_exif(self, img_obj):
        choosen_date = img_obj.choosen.strftime(
            "%Y:%m:%d %H:%M:%S")
        for k in ImageDateSaver.EXIF_TAGS:
            img_obj.exif_data[k] = choosen_date

    def backup_data(self, img_obj):
        lst = []
        for k, v in img_obj.dates.items():
            lst.append(k+"="+v.strftime("%Y:%m:%d %H:%M:%S"))
        backup_str = ";".join(lst)
        for k in ImageDateSaver.EXIF_BACKUP_TAG:
            img_obj.exif_data[k] = backup_str

    def change_modtime(self, img_obj):
        date = img_obj.choosen
        modTime = time.mktime(date.timetuple())
        os.utime(img_obj.new_name, (modTime, modTime))


class ImageDateChooser():
    CHOOSE_ORDER = [
        "GPSDateTime",
        "DateTimeOriginal",
        "DateTime",
        "DateTimeDigitized",
        "File",
        "Path"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_date = datetime(2000, 1, 1, 0, 0, 0)
        self.max_date = datetime.now()
        for arg in kwargs:
            setattr(self, arg, kwargs[arg])

    def choose(self, img_obj):
        # remove dates from today or behid date fix
        valid_dates = {k: v for k, v in img_obj.dates.items()
                       if self.is_valid_date(v)}

        print("File: {} -> Date: {}".format(img_obj.file_obj.name, valid_dates))

        # choose order
        choosen_date = None
        for name in ImageDateChooser.CHOOSE_ORDER:
            if name in valid_dates:
                date = valid_dates[name]
                if len(valid_dates) == 1:
                    choosen_date = date
                    break
                elif self.has_seconds(date):
                    choosen_date = date
                    break
        return choosen_date

    def has_seconds(self, dt_val):
        return dt_val.hour > 0 or dt_val.minute > 0

    def is_valid_date(self, dt_val):
        return dt_val and dt_val > self.min_date and dt_val < self.max_date


class ImageDateFinder():
    def __init__(self, strategies=None):
        self.strategies = []
        if not strategies:
            strategies = [DateFromExifTag(), DateFromFilePathFolder(),
                          DateFromFileDateTime()]
        for strategy in strategies:
            self.register(strategy)

    def register(self, strategy):
        if hasattr(strategy, 'get_dates'):
            self.strategies.append(strategy)

    def get_dates(self, img_obj):
        for strategy in self.strategies:
            dates = strategy.get_dates(img_obj)
            if dates:
                img_obj.dates.update(dates)
        return img_obj.dates


class DateFromExifTag():

    def __init__(self):
        self.name = 'exif'

    def read_exif_tag(self, exif_dict, etype, key, as_string=False):
        if etype in exif_dict:
            if key in exif_dict[etype]:
                result = exif_dict[etype][key]
                if as_string:
                    return result.decode("utf-8")
                return result
        return None

    def convert_to_timestamp(self, exif_val):
        if exif_val and exif_val.strip(" \\/-"):
            exif_val = exif_val.replace('/', ':')
            exif_val = exif_val.replace('\\', ':')
            exif_val = exif_val.replace('-', ':')
            try:
                return datetime.strptime(exif_val, '%Y:%m:%d %H:%M:%S')
            except ValueError:
                try:
                    return datetime.strptime(exif_val, '%Y:%m:%d')
                except ValueError:
                    pass
        return None

    def get_dates(self, img_obj):
        exif_dict = img_obj.exif_data
        new_dict = {}
        new_dict["DateTime"] = self.read_exif_tag(
            exif_dict, "0th", piexif.ImageIFD.DateTime, as_string=True)
        new_dict["DateTimeOriginal"] = self.read_exif_tag(
            exif_dict, "0th", piexif.ExifIFD.DateTimeOriginal, as_string=True)
        new_dict["DateTimeDigitized"] = self.read_exif_tag(
            exif_dict, "0th", piexif.ExifIFD.DateTimeDigitized, as_string=True)
        new_dict["GPSDateTime"] = self.get_gps_datetime(exif_dict)
        return {k: self.convert_to_timestamp(v) for k, v in new_dict.items()}

    def get_gps_datetime(self,exif_dict):
        b_gpsdate = self.read_exif_tag(
            exif_dict, "GPS", piexif.GPSIFD.GPSDateStamp)
        t_gpstime = self.read_exif_tag(
            exif_dict, "GPS", piexif.GPSIFD.GPSTimeStamp)
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



class DateFromFilePathFolder():
    RE = re.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}")
    RE_YEAR = re.compile("^[0-9]{4}\\s")

    def __init__(self):
        self.name = 'path'

    def get_dates(self, img_obj):
        adate = self.str_to_date(self.find_date_or_year(img_obj))
        if adate:
            return {'Path': adate}
        return {}

    def str_to_date(self, adate):
        if adate:
            dt_parts = adate.split("-")
            dt_parts += ['01'] * (3 - len(dt_parts))
            dt_parts = list(map(int, dt_parts))
            try:
                return datetime(dt_parts[0], dt_parts[1], dt_parts[2], 0, 0, 0)
            except ValueError:
                pass
        return None

    def find_date_or_year(self, img_obj):
        file_obj = img_obj.file_obj
        for path in file_obj.parents:
            res = DateFromFilePathFolder.RE.search(path.stem)
            if (res):
                return res.group(0)
            else:
                res = DateFromFilePathFolder.RE_YEAR.search(path.stem)
                if (res):
                    return res.group(0)
        return None


class DateFromFileDateTime():

    def __init__(self):
        self.name = 'file'

    def get_dates(self, obj_img):
        adate = self.creation_date(obj_img.file_obj)
        if adate:
            return {'File': datetime.fromtimestamp(adate)}
        return {}

    def creation_date(self, path_to_file):
        if platform.system() == 'Windows':
            return os.path.getctime(path_to_file)
        else:
            stat = os.stat(path_to_file)
            try:
                return stat.st_birthtime
            except AttributeError:
                # We're probably on Linux. No easy way to get creation dates here,
                # so we'll settle for when its content was last modified.
                return stat.st_mtime


if __name__ == "__main__":
    main()
