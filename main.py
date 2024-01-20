import os
import logging
import pytz
from datetime import datetime, time, date
from telegram.ext import filters
from dateutil.relativedelta import relativedelta
from telegram import ReplyKeyboardMarkup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler
from util import connect
from tzwhere import tzwhere


GOAL_PERIODS = ["Monthly", "3-Month", "6-Month", "Yearly"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user.name.split(' ')[0]
    reply_buttons = GOAL_PERIODS
    await context.bot.send_message(chat_id, f"Hi {user}! Set your goal. First choose the period",
                             reply_markup=ReplyKeyboardMarkup([reply_buttons],
                                                              one_time_keyboard=True,
                                                              resize_keyboard=True))


async def location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_location = update.message.location
    tzwhere_class = tzwhere.tzwhere()
    timezone_str = tzwhere_class.tzNameAt(user_location.latitude, user_location.longitude)
    context.user_data["timezone"] = timezone_str
    await context.bot.send_message(chat_id, f"Enter the total number of steps you want to complete")


async def goal_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    months_from_now = {"Monthly": 1, "3-Month": 3, "6-Month": 6, "Yearly": 12}[update.message.text]
    exact_date = datetime.today() + relativedelta(months=months_from_now) - relativedelta(days=1)
    rounded_date = datetime.today() + relativedelta(months=months_from_now)
    if months_from_now == 12:
        rounded_date -= relativedelta(months=rounded_date.month - 1)
    rounded_date -= relativedelta(days=rounded_date.day)
    # TODO: fix formatting
    reply_buttons = list(set(datetime.date(d).strftime('%Y/%m/%d') for d in (exact_date, rounded_date)))
    await context.bot.send_message(chat_id, f"Choose the last day of the challenge",
                                   reply_markup=ReplyKeyboardMarkup([reply_buttons],
                                                                    one_time_keyboard=True,
                                                                    resize_keyboard=True))


async def set_final_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["final_date"] = update.message.text
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id,
                                   f"Send your current location so we can determine your time zone for notifications")


async def remind(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(f'select chat_id from users where chat_id={chat_id}')
    results = cursor.fetchone()
    conn.close()
    if results:
        await context.bot.send_message(chat_id, f"How many steps have you walked today?")


async def number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    steps = int(update.message.text)
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(f'select chat_id, steps, goal, due_date from users where chat_id={chat_id}')
    results = cursor.fetchone()
    if context.user_data.get('change_goal'):
        context.user_data["change_goal"] = False
        cursor.execute(f'update users set goal={steps} where chat_id={chat_id}')
        conn.commit()
        conn.close()
        await context.bot.send_message(chat_id, "Your goal has been updated")
    elif results:
        days_left = (results[3] - date.today()).days
        avg_daily_steps = (results[2] - results[1] - steps) // days_left
        if avg_daily_steps < 0:
            cursor.execute(f'delete from users where chat_id={chat_id}')
            await context.bot.send_message(chat_id, "You achieved your goal! Congratulations!")
        else:
            cursor.execute(f'update users set steps=steps+{steps} where chat_id={chat_id}')
            await context.bot.send_message(chat_id, f"""Your challenge: {results[2]} steps before {results[3]}
Current result: {results[1] + steps}
Days left: {days_left}
Avg number of steps per day to succeed: {avg_daily_steps}""")
        conn.commit()
        conn.close()
    else:
        conn.close()
        await set_goal(update, context)


async def set_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    final_date = context.user_data["final_date"]
    steps = int(update.message.text)
    conn = connect()
    cursor = conn.cursor()
    start_value = 0
    tz = context.user_data["timezone"]
    cursor.execute(f"""insert into users (chat_id, timezone, due_date, goal, steps) values 
        ({chat_id}, '{tz}', '{final_date}', {steps}, {start_value});""")
    conn.commit()
    conn.close()
    context.job_queue.run_daily(lambda x: remind(x, chat_id),
                                time=time(hour=23, minute=0, tzinfo=pytz.timezone(tz)))

    await context.bot.send_message(chat_id, f"""All set! You will be asked daily at 23:00. 
If you have already walked some steps towards the goal, type in the initial number""")


async def change_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.user_data["change_goal"] = True
    await context.bot.send_message(chat_id, "Enter new goal")


async def remove_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(f'delete from users where chat_id={chat_id}')
    conn.commit()
    conn.close()
    await context.bot.send_message(chat_id, "Your goal has been removed. Use /start to set another one if you wish.")


def add_existing_users(application):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute('select chat_id, timezone from users')
    results = cursor.fetchall()

    def one_iteration(_chat_id, _tz):
        async def callback(context):
            await remind(context, _chat_id)
        application.job_queue.run_daily(callback, time=time(hour=23, minute=0, tzinfo=pytz.timezone(_tz)))

    for (chat_id, tz) in results:
        one_iteration(chat_id, tz)
    conn.close()


if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    TOKEN = os.environ["BOT_TOKEN"]
    URL = f"https://api.telegram.org/bot{TOKEN}"
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.DEBUG)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("changegoal", change_goal))
    app.add_handler(CommandHandler("removegoal", remove_goal))
    app.add_handler(MessageHandler(filters.Regex('(\d\-Month)|(Yearly)|(Monthly)'), goal_type))
    app.add_handler(MessageHandler(filters.Regex('\d{4}/\d{2}/\d{2}'), set_final_date))
    app.add_handler(MessageHandler(filters.Regex('^\d+$'), number))
    app.add_handler(MessageHandler(filters.LOCATION, location))
    add_existing_users(app)
    app.run_polling()
