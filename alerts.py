from dotenv.main import DotEnv
from telegram.ext import Updater
from dotenv import load_dotenv


token = load_dotenv('./env')

print(token)
