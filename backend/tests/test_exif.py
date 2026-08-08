from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, PropertyMock

import pytest
from PIL import Image

from app.search.exif import extract_capture_time, extract_gps


def _mock_exif(
    tags: dict | None = None,
    gps_ifd: dict | None = None,
    exif_ifd: dict | None = None,
) -> MagicMock:
    exif = MagicMock()
    if tags is None:
        tags = {}
    exif.__getitem__.side_effect = lambda k: tags.get(k)
    exif.get.side_effect = lambda k, default=None: tags.get(k, default)
    ifds = {}
    if gps_ifd is not None:
        ifds[0x8825] = gps_ifd
    if exif_ifd is not None:
        ifds[0x8769] = exif_ifd
    exif.get_ifd.side_effect = lambda tag: ifds.get(tag, {})
    return exif


def _mock_img(exif: MagicMock | None = None) -> MagicMock:
    img = MagicMock(spec=Image.Image)
    if exif is not None:
        img.getexif.return_value = exif
    else:
        img.getexif.return_value = _mock_exif()
    return img


# --- extract_capture_time ---


class TestExtractCaptureTime:
    def test_prefers_datetime_original(self) -> None:
        exif = _mock_exif(
            tags={
                0x9003: "2024:01:15 10:30:00",
                0x9011: "+05:30",
            }
        )
        img = _mock_img(exif)
        result = extract_capture_time(img)
        assert result is not None
        assert result == datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone(timedelta(hours=5, minutes=30))
        )

    def test_negative_offset(self) -> None:
        exif = _mock_exif(
            tags={
                0x9003: "2024:06:15 08:00:00",
                0x9011: "-08:00",
            }
        )
        img = _mock_img(exif)
        result = extract_capture_time(img)
        assert result is not None
        assert result == datetime(2024, 6, 15, 8, 0, 0, tzinfo=timezone(timedelta(hours=-8)))

    def test_fallback_to_datetime_digitized(self) -> None:
        exif = _mock_exif(
            tags={
                0x9004: "2024:03:20 14:00:00",
                0x9012: "+00:00",
            }
        )
        img = _mock_img(exif)
        result = extract_capture_time(img)
        assert result is not None
        assert result == datetime(2024, 3, 20, 14, 0, 0, tzinfo=timezone.utc)

    def test_prefers_original_over_digitized(self) -> None:
        exif = _mock_exif(
            tags={
                0x9003: "2024:01:15 10:30:00",
                0x9011: "+05:30",
                0x9004: "2024:03:20 14:00:00",
                0x9012: "+00:00",
            }
        )
        img = _mock_img(exif)
        result = extract_capture_time(img)
        assert result is not None
        assert result == datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone(timedelta(hours=5, minutes=30))
        )

    def test_none_when_datetime_original_missing_offset(self) -> None:
        exif = _mock_exif(tags={0x9003: "2024:01:15 10:30:00"})
        img = _mock_img(exif)
        assert extract_capture_time(img) is None

    def test_none_when_no_datetime_tags(self) -> None:
        exif = _mock_exif(tags={})
        img = _mock_img(exif)
        assert extract_capture_time(img) is None

    def test_none_when_no_exif(self) -> None:
        exif = _mock_exif()
        exif.__bool__.return_value = False
        img = _mock_img(exif)
        assert extract_capture_time(img) is None

    def test_none_when_no_exif_data_mock(self) -> None:
        img = _mock_img()
        img.getexif.return_value.__bool__.return_value = False
        assert extract_capture_time(img) is None

    def test_none_when_datetime_digitized_missing_offset(self) -> None:
        exif = _mock_exif(tags={0x9004: "2024:03:20 14:00:00"})
        img = _mock_img(exif)
        assert extract_capture_time(img) is None

    def test_sub_ifd_tags_are_read(self) -> None:
        exif = _mock_exif(
            exif_ifd={
                0x9003: "2024:05:10 09:00:00",
                0x9011: "-07:00",
            }
        )
        img = _mock_img(exif)
        result = extract_capture_time(img)
        assert result is not None
        assert result == datetime(2024, 5, 10, 9, 0, 0, tzinfo=timezone(timedelta(hours=-7)))

    def test_sub_ifd_takes_precedence_over_top_level(self) -> None:
        exif = _mock_exif(
            tags={
                0x9003: "2024:01:15 10:30:00",
                0x9011: "+05:30",
            },
            exif_ifd={
                0x9003: "2024:06:15 14:30:00",
                0x9011: "+05:30",
            },
        )
        img = _mock_img(exif)
        result = extract_capture_time(img)
        assert result is not None
        assert result == datetime(
            2024, 6, 15, 14, 30, 0, tzinfo=timezone(timedelta(hours=5, minutes=30))
        )

    def test_sub_ifd_offset_only(self) -> None:
        exif = _mock_exif(
            tags={0x9003: "2024:01:15 10:30:00"},
            exif_ifd={0x9011: "+05:30"},
        )
        img = _mock_img(exif)
        result = extract_capture_time(img)
        assert result is not None
        assert result == datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone(timedelta(hours=5, minutes=30))
        )

    def test_falls_through_to_digitized_when_original_incomplete(self) -> None:
        exif = _mock_exif(
            tags={
                0x9003: "2024:01:15 10:30:00",
                0x9004: "2024:03:20 14:00:00",
                0x9012: "+00:00",
            }
        )
        img = _mock_img(exif)
        result = extract_capture_time(img)
        assert result is not None
        assert result == datetime(2024, 3, 20, 14, 0, 0, tzinfo=timezone.utc)

    def test_falls_through_when_original_datetime_unparseable(self) -> None:
        exif = _mock_exif(
            tags={
                0x9003: "not-a-date",
                0x9011: "+05:30",
                0x9004: "2024:03:20 14:00:00",
                0x9012: "+00:00",
            }
        )
        img = _mock_img(exif)
        result = extract_capture_time(img)
        assert result is not None
        assert result == datetime(2024, 3, 20, 14, 0, 0, tzinfo=timezone.utc)

    def test_none_only_when_no_pair_complete(self) -> None:
        exif = _mock_exif(
            tags={
                0x9003: "2024:01:15 10:30:00",
                0x9004: "2024:03:20 14:00:00",
            }
        )
        img = _mock_img(exif)
        assert extract_capture_time(img) is None

    def test_none_when_sub_ifd_original_unparseable_and_no_complete_pair(self) -> None:
        exif = _mock_exif(exif_ifd={0x9003: "not-a-date", 0x9011: "+05:30"})
        img = _mock_img(exif)
        assert extract_capture_time(img) is None


# --- extract_gps ---


class TestExtractGps:
    def test_valid_gps_coordinates(self) -> None:
        gps_ifd = {
            0x0001: "N",
            0x0002: (40, 30, 0),
            0x0003: "W",
            0x0004: (74, 0, 0),
        }
        exif = _mock_exif(gps_ifd=gps_ifd)
        img = _mock_img(exif)
        result = extract_gps(img)
        assert result is not None
        lat, lon = result
        assert abs(lat - 40.5) < 0.001
        assert abs(lon - (-74.0)) < 0.001

    def test_gps_dms_with_seconds(self) -> None:
        gps_ifd = {
            0x0001: "S",
            0x0002: (33, 51, 30),
            0x0003: "E",
            0x0004: (151, 12, 0),
        }
        exif = _mock_exif(gps_ifd=gps_ifd)
        img = _mock_img(exif)
        result = extract_gps(img)
        assert result is not None
        lat, lon = result
        expected_lat = -(33 + 51 / 60 + 30 / 3600)
        expected_lon = 151 + 12 / 60
        assert abs(lat - expected_lat) < 0.001
        assert abs(lon - expected_lon) < 0.001

    def test_none_when_gps_ifd_absent(self) -> None:
        exif = _mock_exif()
        img = _mock_img(exif)
        assert extract_gps(img) is None

    def test_none_when_no_exif(self) -> None:
        exif = _mock_exif()
        exif.__bool__.return_value = False
        img = _mock_img(exif)
        assert extract_gps(img) is None

    def test_none_when_lat_missing(self) -> None:
        gps_ifd = {
            0x0001: "N",
            0x0003: "W",
            0x0004: (74, 0, 0),
        }
        exif = _mock_exif(gps_ifd=gps_ifd)
        img = _mock_img(exif)
        assert extract_gps(img) is None

    def test_none_when_lon_missing(self) -> None:
        gps_ifd = {
            0x0001: "N",
            0x0002: (40, 30, 0),
            0x0003: "W",
        }
        exif = _mock_exif(gps_ifd=gps_ifd)
        img = _mock_img(exif)
        assert extract_gps(img) is None

    def test_none_when_lat_out_of_bounds(self) -> None:
        gps_ifd = {
            0x0001: "N",
            0x0002: (100, 0, 0),
            0x0003: "W",
            0x0004: (74, 0, 0),
        }
        exif = _mock_exif(gps_ifd=gps_ifd)
        img = _mock_img(exif)
        assert extract_gps(img) is None

    def test_none_when_lon_out_of_bounds(self) -> None:
        gps_ifd = {
            0x0001: "N",
            0x0002: (40, 0, 0),
            0x0003: "W",
            0x0004: (200, 0, 0),
        }
        exif = _mock_exif(gps_ifd=gps_ifd)
        img = _mock_img(exif)
        assert extract_gps(img) is None

    def test_none_when_bounds_edge_cases(self) -> None:
        gps_ifd = {
            0x0001: "N",
            0x0002: (90, 0, 0),
            0x0003: "E",
            0x0004: (180, 0, 0),
        }
        exif = _mock_exif(gps_ifd=gps_ifd)
        img = _mock_img(exif)
        result = extract_gps(img)
        assert result is not None

    def test_none_when_dms_tuple_invalid(self) -> None:
        gps_ifd = {
            0x0001: "N",
            0x0002: "invalid",
            0x0003: "W",
            0x0004: (74, 0, 0),
        }
        exif = _mock_exif(gps_ifd=gps_ifd)
        img = _mock_img(exif)
        assert extract_gps(img) is None
