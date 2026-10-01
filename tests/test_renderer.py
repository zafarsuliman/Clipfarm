from clipfarm.editing.renderer import crop_for, smooth_track


def test_crop_for_vertical_from_landscape():
    cw, ch, x, y = crop_for(1920, 1080, 1080, 1920)
    assert cw < 1920
    assert ch == 1080
    assert x >= 0
    assert y == 0


def test_smooth_track_stays_in_bounds():
    track = [(0.0, 100.0), (0.25, 300.0), (0.5, None), (0.75, 1800.0)]
    output = smooth_track(track, 1920, 608)
    half = 304
    assert output
    assert all(half <= x <= 1920 - half for _, x in output)
