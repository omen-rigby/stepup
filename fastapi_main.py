import os
from contextlib import asynccontextmanager
from http import HTTPStatus
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from fastapi import FastAPI, Request, Response
from commands import *


# Initialize python telegram bot
ptb = (
    Application.builder()
    .updater(None)
    .token(os.environ["TOKEN"])
    .read_timeout(7)
    .get_updates_read_timeout(42)
    .build()
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.environ.get('WEBHOOK'):
        await ptb.bot.setWebhook(os.environ['WEBHOOK'])
    async with ptb:
        await ptb.start()
        yield
        await ptb.stop()

# Initialize FastAPI app (similar to Flask)
app = FastAPI(lifespan=lifespan)


@app.post("/")
async def process_update(req: Request):
    jason = await req.json()
    update = Update.de_json(jason, ptb.bot)
    await ptb.process_update(update)
    return Response(status_code=HTTPStatus.OK)


ptb.add_handler(CommandHandler("start", start))
ptb.add_handler(CommandHandler("changegoal", change_goal))
ptb.add_handler(CommandHandler("removegoal", remove_goal))
ptb.add_handler(MessageHandler(filters.Regex('(\d\-Month)|(Yearly)|(Monthly)'), goal_type))
ptb.add_handler(MessageHandler(filters.Regex('\d{4}/\d{2}/\d{2}'), set_final_date))
ptb.add_handler(MessageHandler(filters.Regex('^\d+$'), number))
ptb.add_handler(MessageHandler(filters.LOCATION, location))
add_existing_users(ptb)
