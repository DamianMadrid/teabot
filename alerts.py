from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import dotenv_values
from subprocess import check_output
from scrapper import Scrapper
from datetime import datetime
import pickle
import time
import os


config =dotenv_values('.env')
TELEGRAM_TOKEN = config["TELEGRAM_TOKEN"]
DATA_PATH = os.path.expanduser("~/YARAPT/data/")
SUB_DATA_PATH = DATA_PATH+"subscriptions.csv"
updater = Updater(TELEGRAM_TOKEN)
main_scrapper = Scrapper(DATA_PATH)
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
    current_exec  = str(time.mktime(datetime.now().timetuple())).replace(".",":")
    update_str = main_scrapper.updateSavedProd(current_exec)
    job = context.job
    if update_str:
        context.bot.send_message(job.context,update_str)
    update_str = main_scrapper.updateString(current_exec)
    if update_str:
        context.bot.send_message(job.context,update_str)
    else:
        print(f"There was no update {datetime.now()}")

def _subscribe(update:Update, context:CallbackContext)->None:
    global active_subs
    chat_id = update.message.chat_id
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
        updater.bot.sendMessage(sub,"Bot back online",)
        dispatcher.job_queue.run_once(sendUpdate,10,context=sub,name=f"resume with:{sub}",job_kwargs = {"max_instances":2,"misfire_grace_time":None})
        dispatcher.job_queue.run_repeating(sendUpdate,3600,context=sub,name=str(sub),job_kwargs = {"max_instances":2,"misfire_grace_time":None})

def _addProd(update:Update, context:CallbackContext)->None:
    command_args = update.message.text.split(" ")[1:]
    if len(command_args) in [1,2]:
        if len(command_args) == 2:
            try:
                float(command_args[1])
                add_result = main_scrapper.addProd(command_args[0],command_args[1])
                update.message.reply_text("Product Added succesfully" if add_result else "Failed to add")
                return
            except:
                update.message.reply_text("Goal not valid")
                return
        add_result = main_scrapper.addProd(command_args[0])
        update.message.reply_text("Product added succesfully" if add_result else "Failed to add")
        return
    else:
        update.message.reply_text("Args are /addProd url|str (goal|float)")
        return

def _checkWishlists(update:Update, context:CallbackContext)->None:
    result = main_scrapper.checkWishList()
    update.message.reply_text(result)
    return

def _removeProd(update:Update, context:CallbackContext)->None:
    command_args = update.message.text.split(" ")[1:]
    if len(command_args) ==1:
        remove_result =  main_scrapper.removeProd(command_args[0])
        update.message.reply_text("Product removed succesfully" if remove_result else "Failed to remove")
        return
    else:
        update.message.reply_text("Args are /addProd url|str")
        return

def _errorUpdate(update:Update, context:CallbackContext)->None:
    for sub in active_subs:
        updater.bot.sendMessage(sub,"An error ocurrend")
        updater.bot.sendMessage(sub,str(type(context.error)))
        
    
    

def main():
    print("Bot startup")
    loadSubList()
    _resumeSubscription()
    dispatcher.add_handler(CommandHandler("whereareyou", _whereAreYouCmmnd))
    dispatcher.add_handler(CommandHandler("subscribe", _subscribe))
    dispatcher.add_handler(CommandHandler("addprod", _addProd))
    dispatcher.add_handler(CommandHandler("removeprod", _removeProd))
    dispatcher.add_handler(CommandHandler("checkwishlists", _checkWishlists))
    # dispatcher.add_error_handler(_errorUpdate)
    updater.start_polling()
    print("Bot listening")
    updater.idle()

if __name__ == '__main__':
        main()
