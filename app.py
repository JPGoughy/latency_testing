from flask import Flask
from flask_restx import Api, Resource


app = Flask(__name__)
api = Api(
    app,
    title="Latency API",
    description="A simple API returning small snippets of content",
    errors={
        "NotFound": {"message": "Could not find requested resource", "status": 404}
    },
)


@api.route("/latency_test", methods=["GET"])
class latency_test(Resource):
    def get(self):
        return {"message": "Hello from Wavelength!"}, 200

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5006,
        debug=True,
    )

