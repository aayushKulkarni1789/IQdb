from io import BytesIO

from PIL import Image

from app.core.thumbnails import make_thumbnail_jpeg


def test_thumbnail_landscape_resizes_longest_edge():
    img = Image.new("RGB", (800, 400), color="red")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    data = buf.getvalue()

    thumb = make_thumbnail_jpeg(data, max_dim=256)
    with Image.open(BytesIO(thumb)) as out:
        assert out.format == "JPEG"
        assert max(out.size) <= 256
        # landscape: width should be 256
        assert out.size[0] == 256


def test_thumbnail_portrait_resizes_longest_edge():
    img = Image.new("RGB", (400, 800), color="blue")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    data = buf.getvalue()

    thumb = make_thumbnail_jpeg(data, max_dim=256)
    with Image.open(BytesIO(thumb)) as out:
        assert out.format == "JPEG"
        assert max(out.size) <= 256
        assert out.size[1] == 256


def test_thumbnail_small_image_not_upscaled_but_jpeg():
    img = Image.new("RGB", (100, 50), color="green")
    buf = BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()

    thumb = make_thumbnail_jpeg(data, max_dim=256)
    with Image.open(BytesIO(thumb)) as out:
        assert out.format == "JPEG"
        assert out.size == (100, 50)
        assert max(out.size) <= 256


def test_thumbnail_rgba_converted():
    img = Image.new("RGBA", (500, 500), color=(255, 0, 0, 128))
    buf = BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()

    thumb = make_thumbnail_jpeg(data, max_dim=256)
    with Image.open(BytesIO(thumb)) as out:
        assert out.format == "JPEG"
        assert max(out.size) == 256
        assert out.mode == "RGB"
