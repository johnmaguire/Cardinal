from contextlib import contextmanager

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
