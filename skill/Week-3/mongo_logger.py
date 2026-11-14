"""MongoDB connection and request logging."""

from datetime import datetime, timezone

from pymongo import MongoClient


class MongoLogger:
    def __init__(self, uri="mongodb://localhost:27017/"):
        self.client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        # Check availability now so the CLI can warn and continue with AI alone.
        try:
            self.client.admin.command("ping")
            self.database = self.client["llm_monitoring"]
            if "call_logs" not in self.database.list_collection_names():
                self.database.create_collection("call_logs")
            self.collection = self.database["call_logs"]
        except Exception:
            self.client.close()
            raise

    def log_request(self, document):
        saved_document = dict(document)
        saved_document["timestamp"] = datetime.now(timezone.utc)
        self.collection.insert_one(saved_document)

    def close(self):
        self.client.close()
