def read_arrow(path):
    import pyarrow.dataset as ds
    from pyxet import XetFS
    return ds.dataset(path, filesystem=XetFS())
