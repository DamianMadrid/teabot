from telegram import Update, chatinvitelink, update
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import dotenv_values
from subprocess import check_output
from amazonScraper_rbpi import generate_Update
from datetime import datetime
import pickle
import os


config =dotenv_values('.env')
TELEGRAM_TOKEN = config["TELEGRAM_TOKEN"]
SUB_DATA_PATH = os.path.join(os.path.expanduser("~"),"YARAPT/data/subscriptions.csv")

updater = Updater(TELEGRAM_TOKEN)
dispatcher = updater.dispatcher
active_subs = None

def dumpSubList():
    global active_subs
    with open(SUB_DATA_PATH,"wb+") as fp:
        pickle.dump(active_subs,fp)

def loadSubList():
    global active_subs
    with open(SUB_DATA_PATH,"rb") as fp:
        active_subs = pickle.load(fp)

def sendUpdate(context:CallbackContext)->None:
    update_str = generate_Update()
    #update_str = "Testing"
    if update_str:
        job = context.job
        context.bot.send_message(job.context,update_str)
    else:
        print(f"There was no update {datetime.now()}")



def _subscribe(update:Update, context:CallbackContext)->None:
    global active_subs
    chat_id = update.message.chat_id
    print(chat_id,type(chat_id))
    print("Bot: new subscriber")
    if chat_id in active_subs:
        print("Already subbed")
        update.message.reply_text("You're already subbed!")
        return;
    active_subs.append(chat_id)
    dumpSubList()
    context.job_queue.run_once(sendUpdate,5,context=chat_id,name=f"once:{chat_id}")
    context.job_queue.run_repeating(sendUpdate,3600,context=chat_id,name=str(chat_id))
    update.message.reply_text("Successfully subbed")


def _whereAreYouCmmnd(update:Update, context:CallbackContext)->None:
    ip_addr = check_output("curl -s ifconfig.me" ,shell=True)
    ip_addr = ip_addr.decode("utf-8")
    update.message.reply_text(ip_addr)

def _Ping(update:Update, context:CallbackContext)->None:
    update.message.reply_text("Bot back online")

def _resumeSubscription():
    for sub in active_subs:
        print (f"Resuming sub with: {sub}")
        print(type(sub))
        updater.bot.sendMessage(sub,"Bot back online",)
        dispatcher.job_queue.run_repeating(sendUpdate,3600,context=sub,name=str(sub),job_kwargs = {"max_instances":2,"misfire_grace_time":None})

def main():
    print("Bot startup")
    loadSubList()
    _resumeSubscription()
    dispatcher.add_handler(CommandHandler("WhereAreYou", _whereAreYouCmmnd))
    dispatcher.add_handler(CommandHandler("Subscribe", _subscribe))
    updater.start_polling()
    print("Bot listening")
    updater.idle()

if __name__ == '__main__':
	main()

