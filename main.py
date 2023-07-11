# Welcome to the Poe API tutorial. The starter code provided provides you with a quick way to get
# a bot running. By default, the starter code uses the EchoBot, which is a simple bot that echos
# a message back at its user and is a good starting point for your bot, but you can
# comment/uncomment any of the following code to try out other example bots.

from modal import Image, Stub, asgi_app

from yt_summarizer_bot import YTSummarizerBot

# specific to hosting with modal.com
image = Image.debian_slim().pip_install_from_requirements("requirements.txt")
stub = Stub("yt-summarizer-bot")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    from fastapi_poe import make_app

    bot = YTSummarizerBot()

    POE_API_KEY = "j87ihqtkviux33dVDatxOrroHcvD1od3"
    app = make_app(bot, api_key=POE_API_KEY)
    return app
