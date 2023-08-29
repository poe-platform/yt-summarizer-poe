import os
from fastapi_poe import make_app
from modal import Image, Secret, Stub, asgi_app

from yt_summarizer_bot import YTSummarizerBot

# specific to hosting with modal.com
image = Image.debian_slim().pip_install_from_requirements("requirements.txt")
stub = Stub("yt-summarizer-app")


@stub.function(image=image, secret=Secret.from_name("yt-summarizer-secret"))
@asgi_app()
def fastapi_app():
    bot = YTSummarizerBot()
    app = make_app(bot, access_key=os.environ["POE_ACCESS_KEY"])
    return app
