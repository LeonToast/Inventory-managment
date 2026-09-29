import itertools
from types import SimpleNamespace

from pymongo.errors import DuplicateKeyError

_ids = itertools.count(1)


def _matches(item, query):
    # `_id` values are compared as text, because the routers pass ObjectId and the fakes use strings.
    return all(
        (str(item.get(key)) == str(value)) if key == "_id" else item.get(key) == value
        for key, value in query.items()
    )


class FakeCursor(list):
    """What `find().sort()` returns: a list that also has the cursor's `limit`."""

    def limit(self, count):
        return FakeCursor(self[:count])

    def skip(self, count):
        return FakeCursor(self[count:])


class FakeCollection(list):
    """In-memory stand-in for a MongoDB collection, used by the tests. Documents are dicts."""

    unique_field = None

    def create_index(self, *_args, **_kwargs):
        return "index"

    def find(self, query=None, _projection=None):
        return type(self)(item for item in self if _matches(item, query or {}))

    def sort(self, key, direction=1):
        # Ties keep insertion order, so "newest first" is well defined even for equal timestamps.
        ordered = sorted(
            enumerate(self), key=lambda pair: (pair[1][key], pair[0]), reverse=direction == -1
        )
        return FakeCursor(item for _, item in ordered)

    def find_one(self, query, _projection=None):
        return next((item for item in self if _matches(item, query)), None)

    def insert_one(self, document):
        field = self.unique_field
        if field and any(item[field] == document[field] for item in self):
            raise DuplicateKeyError(f"duplicate {field}")
        document = {**document, "_id": f"{next(_ids):024x}"}  # 24 hex characters, in creation order
        self.append(document)
        return SimpleNamespace(inserted_id=document["_id"])

    def find_one_and_update(self, query, update, return_document=None):
        item = self.find_one(query)
        if item:
            item.update(update["$set"])
        return dict(item) if item else None

    def delete_one(self, query):
        item = self.find_one(query)
        if item:
            self.remove(item)
        return SimpleNamespace(deleted_count=1 if item else 0)


class FakeMaterials(FakeCollection):
    pass


class FakeReports(FakeCollection):
    unique_field = "serial_number"


class FakeAnnouncements(FakeCollection):
    pass


class FakeActivity(FakeCollection):
    pass

