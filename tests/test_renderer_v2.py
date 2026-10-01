from clipfarm.editing.renderer_v2 import _keep_ranges, _remap_time

def test_keep_ranges_remove_cut():
    keeps = _keep_ranges(
        0.0, 10.0,
        [{"type": "trim_silence", "start": 3.0, "end": 4.0}],
    )
    assert keeps == [(0.0, 3.0), (4.0, 10.0)]

def test_remap_time():
    keeps = [(0.0, 3.0), (4.0, 10.0)]
    assert _remap_time(2.0, keeps) == 2.0
    assert _remap_time(5.0, keeps) == 4.0
