from flask import Flask, jsonify, request

app = Flask(__name__)

APPLICATION = "echo-lab"


@app.get("/")
def root() -> tuple:
    return jsonify({"status": "ok", "application": APPLICATION}), 200


@app.get("/health")
def health() -> tuple:
    return jsonify({"status": "ok", "service": "echo-api"}), 200


@app.get("/echo")
def echo() -> tuple:
    message = request.args.get("msg", "")
    return jsonify({"echo": message}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
