from flask import Flask, jsonify

app = Flask(__name__)

APPLICATION = "konflux-lab"


@app.get("/")
def root() -> tuple:
    return jsonify({"status": "ok", "application": APPLICATION}), 200


@app.get("/health")
def health() -> tuple:
    return jsonify({"status": "ok", "service": "hello-api"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
