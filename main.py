import json
import os

import firebase_admin
from fastapi_poe import make_app
from firebase_admin import credentials, db
from modal import Image, Secret, Stub, asgi_app

from yt_summarizer_bot import YTSummarizerBot

# specific to hosting with modal.com
image = Image.debian_slim().pip_install_from_requirements("requirements.txt")
stub = Stub("yt-summarizer-app")


@stub.function(image=image, secret=Secret.from_name("yt-summarizer-secret"))
@asgi_app()
def fastapi_app():
    cred = credentials.Certificate(json.loads(os.environ["FIREBASE_KEY_JSON"]))
    firebase_admin.initialize_app(
        cred, {"databaseURL": "https://yt-summarizer-poe-default-rtdb.firebaseio.com/"}
    )

    bot = YTSummarizerBot()
    app = make_app(bot, access_key=os.environ["POE_ACCESS_KEY"])
    return app
