import os

import redis
from flask import Flask, jsonify
from pymongo import MongoClient

app = Flask(__name__)

mongo = MongoClient(os.environ["MONGO_URL"])
db = mongo["ticketflash"]
cache = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)


@app.get("/health")
def health():
    mongo.admin.command("ping")
    cache.ping()
    return jsonify(mongo="ok", redis="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
