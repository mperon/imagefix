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


def main():
    processor = ImageProcessor(Path(main_dir))
    processor.run()


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
        self.choosen = None


class ImageProcessor():

    def __init__(self, main_dir=None, make_backup=False, date_finder=None,
                 date_chooser=None, date_saver=None, accept_extensions=None, dest_dir=None):
        super().__init__()
        self.main_dir = main_dir
        self.make_backup = make_backup
        if date_finder:
            self.date_finder = date_finder
        else:
            self.date_finder = ImageDateFinder(processor=self)
        if date_chooser:
            self.date_chooser = date_chooser
        else:
            self.date_chooser = ImageDateChooser(processor=self)
        if date_saver:
            self.date_saver = date_saver
        else:
            self.date_saver = ImageDateSaver(processor=self)
        if accept_extensions:
            self.accept_extensions = accept_extensions
        else:
            self.accept_extensions = (".jpg", ".jpeg",)
        if dest_dir:
            self.dest_dir = dest_dir
        else:
            self.dest_dir = self.main_dir

    def run(self):
        directory = Path(self.main_dir)
        self.walk(directory)

    def walk(self, directory):
        for f in directory.iterdir():
            if f.is_file():
                if str(f).lower().endswith(self.accept_extensions):
                    self.process(f)
            else:
                self.walk(f)

    def process(self, file_obj):
        img_obj = ImgObject(file_obj)

        with Image.open(img_obj.file_obj) as img:
            img_obj.img = img
            img_obj.exif_dict = piexif.load(img.info["exif"])
            # search dates
            self.date_finder.get_dates(img_obj)
            img_obj.choosen = self.date_chooser.choose(img_obj)
            # if img_obj.choosen:
            #     self.date_saver.write(img_obj)


class ImageDateSaver():

    def __init__(self, processor=None):
        super().__init__()

    def write(self, img_obj):
        pass

    def prepare_path(self, f, new_dir):
        relative_path = Path(f).relative_to(main_dir)
        new_path = Path(new_dir).joinpath(relative_path)
        Path(new_path).parent.mkdir(parents=True, exist_ok=True)
        return new_path

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

    def __init__(self, processor=None):
        super().__init__()
        self.min_date = datetime(2000, 1, 1, 0, 0, 0)
        self.max_date = datetime.now()

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
    def __init__(self, processor=None, strategies=None):
        self.strategies = []
        if not strategies:
            strategies = [DateFromExifTag(), DateFromFilePathFolder(),
                          DateFromFileDateTime()]
        for strategy in strategies:
            self.register(strategy)

    def register(self, strategy):
        if hasattr(strategy, 'get_dates'):
            if hasattr(strategy, 'write_dates'):
                self.strategies.append(strategy)

    def get_dates(self, img_obj):
        for strategy in self.strategies:
            dates = strategy.get_dates(img_obj)
            if dates:
                img_obj.dates.update(dates)
        return img_obj.dates

    def write_dates(self, img_obj):
        for strategy in self.strategies:
            strategy.write_dates(img_obj)


class DateFromExifTag():

    DATES_TAGS = [
        ("DateTime", "0th", piexif.ImageIFD.DateTime, ),
        ("DateTimeOriginal", "Exif", piexif.ExifIFD.DateTimeOriginal),
        ("DateTimeDigitized", "Exif", piexif.ExifIFD.DateTimeDigitized, ),
    ]

    def __init__(self, processor=None):
        self._processor = processor
        self.name = 'exif'

    def get_dates(self, img_obj):
        exif_dict = img_obj.exif_dict
        new_dict = {}

        for key, tag, exif_id in DateFromExifTag.DATES_TAGS:
            new_dict[key] = self.read_exif_tag(
                exif_dict, tag, exif_id, as_string=True)

        new_dict["GPSDateTime"] = self.get_gps_datetime(exif_dict)
        return {k: self._convert_to_timestamp(v) for k, v in new_dict.items()}

    def write_dates(self, img_obj):
        choosen = img_obj.choosen
        if choosen:
            choosen_date = choosen.strftime("%Y:%m:%d %H:%M:%S")
            # make backup if necessary
            if self._processor.make_backup:
                self.backup_data(img_obj)
            # write all date tags, except gps
            for _, tag, exif_id in DateFromExifTag.DATES_TAGS:
                self.set_exif_tag(img_obj.exif_dict, tag,
                                  exif_id, choosen_date)

    def backup_data(self, img_obj):
        lst = []
        for k, v in img_obj.dates.items():
            lst.append(k+"="+v.strftime("%Y:%m:%d %H:%M:%S"))
        backup_str = ";".join(lst)
        self.set_exif_tag(img_obj.exif_dict, "Exif",
                          piexif.ExifIFD.UserComment, backup_str)

    def get_gps_datetime(self, exif_dict):
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

    def set_exif_tag(self, exif_dict, etype, key, value):
        if not etype in exif_dict:
            exif_dict[etype] = {}
        exif_dict[etype][key] = value

    def read_exif_tag(self, exif_dict, etype, key, as_string=False):
        if etype in exif_dict:
            if key in exif_dict[etype]:
                result = exif_dict[etype][key]
                if as_string:
                    return result.decode("utf-8")
                return result
        return None

    def _convert_to_timestamp(self, exif_val):
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


class DateFromFilePathFolder():
    RE = re.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}")
    RE_YEAR = re.compile("^[0-9]{4}\\s")

    def __init__(self, processor=None):
        self.name = 'path'

    def get_dates(self, img_obj):
        adate = self.str_to_date(self.find_date_or_year(img_obj))
        if adate:
            return {'Path': adate}
        return {}

    def write_dates(self, img_obj):
        pass

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

    def __init__(self, processor=None):
        self.name = 'file'

    def get_dates(self, obj_img):
        adate = self.creation_date(obj_img.file_obj)
        if adate:
            return {'File': datetime.fromtimestamp(adate)}
        return {}

    def write_dates(self, img_obj):
        pass

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
