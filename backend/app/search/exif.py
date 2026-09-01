import logging
from datetime import datetime, timedelta
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)

# EXIF tag IDs
TAG_EXIF_IFD = 0x8769
TAG_DATETIME_ORIGINAL = 0x9003
TAG_OFFSET_TIME_ORIGINAL = 0x9011
TAG_DATETIME_DIGITIZED = 0x9004
TAG_OFFSET_TIME_DIGITIZED = 0x9012
TAG_GPS_IFD = 0x8825
TAG_GPS_LAT_REF = 0x0001
TAG_GPS_LAT = 0x0002
TAG_GPS_LON_REF = 0x0003
TAG_GPS_LON = 0x0004


def _parse_offset(offset_str: str) -> timedelta | None:
    try:
        sign = 1
        s = offset_str.strip()
        if s.startswith("-"):
            sign = -1
            s = s[1:]
        elif s.startswith("+"):
            s = s[1:]
        parts = s.split(":")
        if len(parts) == 2:
            hours, minutes = int(parts[0]), int(parts[1])
            return timedelta(hours=sign * hours, minutes=sign * minutes)
    except (ValueError, IndexError):
        return None
    return None


def _parse_exif_datetime(dt_str: str) -> datetime | None:
    try:
        return datetime.strptime(dt_str.strip(), "%Y:%m:%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def _dms_to_decimal(
    dms_tuple: tuple,
    ref: str | None,
) -> float | None:
    if dms_tuple is None or len(dms_tuple) != 3:
        return None
    try:
        degrees = float(dms_tuple[0])
        minutes = float(dms_tuple[1])
        seconds = float(dms_tuple[2])
    except (TypeError, ValueError):
        return None
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if ref is not None and ref.upper() in ("S", "W"):
        decimal = -decimal
    return decimal


def _get_tag(exif_data, sub_ifd, tag):
    if sub_ifd is not None:
        value = sub_ifd.get(tag)
        if value is not None:
            return value
    return exif_data.get(tag)


def extract_capture_time(img: Image.Image) -> datetime | None:
    exif_data = img.getexif()
    if not exif_data:
        return None

    sub_ifd = exif_data.get_ifd(TAG_EXIF_IFD)

    datetime_tags = [
        TAG_DATETIME_ORIGINAL,
        TAG_DATETIME_DIGITIZED,
    ]

    for dt_tag in datetime_tags:
        dt_str = _get_tag(exif_data, sub_ifd, dt_tag)
        if dt_str is None:
            continue
        dt = _parse_exif_datetime(str(dt_str))
        if dt is None:
            logger.warning("Failed to parse EXIF datetime tag 0x%04x: %s", dt_tag, dt_str)
            continue
        # Store as naive local time (ADR-0005) - discard timezone offset
        logger.debug("Extracted capture_time: %s", dt.isoformat())
        return dt

    return None


def extract_gps(img: Image.Image) -> Tuple[float, float] | None:
    exif_data = img.getexif()
    if not exif_data:
        return None

    gps_ifd = exif_data.get_ifd(TAG_GPS_IFD)
    if not gps_ifd:
        return None

    lat_ref = gps_ifd.get(TAG_GPS_LAT_REF)
    lat_dms = gps_ifd.get(TAG_GPS_LAT)
    lon_ref = gps_ifd.get(TAG_GPS_LON_REF)
    lon_dms = gps_ifd.get(TAG_GPS_LON)

    if lat_dms is None or lon_dms is None:
        return None

    lat = _dms_to_decimal(lat_dms, lat_ref)
    lon = _dms_to_decimal(lon_dms, lon_ref)

    if lat is None or lon is None:
        logger.warning("Failed to convert GPS DMS to decimal")
        return None

    if not (-90.0 <= lat <= 90.0):
        logger.warning("GPS latitude %f out of bounds [-90, 90]", lat)
        return None
    if not (-180.0 <= lon <= 180.0):
        logger.warning("GPS longitude %f out of bounds [-180, 180]", lon)
        return None

    logger.debug("Extracted GPS: lat=%f, lon=%f", lat, lon)
    return (lat, lon)
