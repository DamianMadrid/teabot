from telegram import Update
from telegram.ext import (Application,CommandHandler,ContextTypes,CallbackContext ,PicklePersistence, MessageHandler,filters)
from dotenv import dotenv_values
from subprocess import check_output
from scrapper import Scrapper
from datetime import datetime
import os

config =dotenv_values('.env')
TELEGRAM_TOKEN = config["TELEGRAM_TOKEN"]
DATA_PATH = os.path.expanduser("./data/")
SUB_DATA_PATH = DATA_PATH+"subscriptions.pickle"
application = Application.builder().token(TELEGRAM_TOKEN).build()
main_scrapper = Scrapper(DATA_PATH)

async def _sendUpdate(context:ContextTypes.DEFAULT_TYPE)->None:
    job = context.job
    main_scrapper.updateSavedProd(str(datetime.now().date()))
    update_str = main_scrapper.updateString(str(datetime.now().date()))
    if update_str:
        await context.bot.send_message(job.chat_id,update_str,parse_mode="HTML")
    else:
#        await context.bot.send_message(job.chat_id,f"No update {str(datetime.now().date())}",parse_mode="HTML")
        print(f"There was no update {datetime.now()}")

async def _forceUpdate(update:Update, context:ContextTypes.DEFAULT_TYPE)->None:
    chat_id = update.effective_message.chat_id
    try:
        context.job_queue.run_repeating(_sendUpdate,interval=3600,first=5, chat_id=chat_id, name=str(chat_id))
    finally:
        pass
    return


async def _getIP(update:Update, context:ContextTypes.DEFAULT_TYPE)->None:
    ip_addr = check_output("curl -s ifconfig.me" ,shell=True)
    ip_addr = ip_addr.decode("utf-8")
    await update.message.reply_text(ip_addr)

async def _Ping(update:Update, context:ContextTypes.DEFAULT_TYPE)->None:
    await update.message.reply_text("Bot back online")

async def _addProd(update:Update, context:ContextTypes.DEFAULT_TYPE)->None:
    command_args = update.message.text.split(" ")[1:]
    if len(command_args) in [1,2]:
        if len(command_args) == 2:
            try:
                float(command_args[1])
                add_result = main_scrapper.addProd(command_args[0],command_args[1])
                await update.message.reply_text("Product Added succesfully" if add_result else "Failed to add")
                return
            except:
                await update.message.reply_text("Goal not valid")
                return
        add_result = main_scrapper.addProd(command_args[0])
        await update.message.reply_text("Product added succesfully" if add_result else "Failed to add")
        return
    else:
        await update.message.reply_text("Args are /addProd url|str (goal|float)")
        return

async def _checkWishlists(update:Update, context:ContextTypes.DEFAULT_TYPE)->None:
    result = main_scrapper.checkWishList()
    await update.message.reply_text(result)
    return

async def _removeProd(update:Update, context:ContextTypes.DEFAULT_TYPE)->None:
    command_args = update.message.text.split(" ")[1:]
    if len(command_args) ==1:
        remove_result =  main_scrapper.removeProd(command_args[0])
        await update.message.reply_text("Product removed succesfully" if remove_result else "Failed to remove")
        return
    else:
        await update.message.reply_text("Args are /addProd url|str")
        return

async def _general(update: Update, context: ContextTypes.DEFAULT_TYPE)->None:
    await update.message.reply_text(update.message.text)
    return



def main():
    persistence = PicklePersistence(filepath="./data/persistance.pckl")
    application = Application.builder().token(TELEGRAM_TOKEN).persistence(persistence).build()
    application.add_handler(CommandHandler("getIP", _getIP))
    application.add_handler(CommandHandler("update", _forceUpdate))
    # application.add_handler(CommandHandler("addprod", _addProd))
    # application.add_handler(CommandHandler("removeprod", _removeProd))
    application.add_handler(CommandHandler("checkwishlists", _checkWishlists))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _general))
    print("Application started succesfully");
    application.run_polling()

if __name__ == '__main__':
        main()
