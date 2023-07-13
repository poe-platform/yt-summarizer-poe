# Welcome to the Poe API tutorial. The starter code provided provides you with a quick way to get
# a bot running. By default, the starter code uses the EchoBot, which is a simple bot that echos
# a message back at its user and is a good starting point for your bot, but you can
# comment/uncomment any of the following code to try out other example bots.

import os

from modal import Image, Secret, Stub, asgi_app

from yt_summarizer_bot import YTSummarizerBot

# specific to hosting with modal.com
image = Image.debian_slim().pip_install_from_requirements("requirements.txt")
stub = Stub("yt-summarizer-app")


@stub.function(image=image, secret=Secret.from_name("yt-summarizer-secret"))
@asgi_app()
def fastapi_app():
    from fastapi_poe import make_app

    bot = YTSummarizerBot()
    POE_API_KEY = os.environ["POE_API_KEY"]
    app = make_app(bot, api_key=POE_API_KEY)
    return app
