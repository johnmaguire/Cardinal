import os
import shutil
import tempfile
from contextlib import contextmanager


@contextmanager
def tempdir(name):
    tempdir_path = os.path.join(tempfile.gettempdir(), name)
    os.mkdir(tempdir_path)
    try:
        yield tempdir_path
    finally:
        shutil.rmtree(tempdir_path)


def get_mock_db():
    db = {}

    def get_db(name, network_specific=True, default=None):
        if default is not None:
            db.update(default)

        @contextmanager
        def mock_db():
            yield db

        return mock_db

    return get_db, db
