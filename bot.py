import json
import logging
import redis
from telegram import (
  ReplyKeyboardMarkup,
  Update
)
from telegram.ext import (
  Updater, 
  CommandHandler, 
  ConversationHandler, 
  MessageHandler, 
  Filters,
  CallbackContext
)

# Setup Redis DB
redis_db = redis.Redis(host='localhost', port=6379, db=0)

# ConversationHandler stuff
CLASS = range(1)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Store JSONs as separate maps in Redis
CLASS_TO_STUDENTS = None
STUDENTS_TO_CLASS = "STUDENTS_TO_CLASS"
USERNAME_TO_IDS = "USERNAME_TO_IDS"
TEACHER_TO_CLASS = "TEACHER_TO_CLASS"
CLASS_TO_TEACHER = "CLASS_TO_TEACHER"
CLASS_TO_MESSAGE_ID = "CLASS_TO_MESSAGE_ID"

########################################
########### COMMON COMMANDS ############
########################################

def start(update: Update, _: CallbackContext) ->  None:
  redis_db.hset(USERNAME_TO_IDS, update.message.from_user.username, update.message.from_user.id)
  update.message.reply_text('Welcome! Your username has been stored in our very secure servers.')

########################################
####### COMMANDS FOR THE TEACHER #######
########################################

def start_attendance_session(update: Update, _: CallbackContext) -> None:
  # Keyboard for choosing class
  keyboard = [
    [class_str for class_str in CLASS_TO_STUDENTS.keys()]
  ]
  reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
  update.message.reply_text('Choose class:', reply_markup=reply_markup)

  return CLASS

def class_handler(update: Update, context: CallbackContext) -> None:
  # Make the current teacher map to selected class as active
  redis_db.hset(TEACHER_TO_CLASS, update.message.from_user.id, update.message.text)
  redis_db.hset(CLASS_TO_TEACHER, update.message.text, update.message.from_user.id)

  # Create attendance message
  message = update.message.reply_text(f'''
    Attendance session for {update.message.text}:
    ''')
  redis_db.hset(CLASS_TO_MESSAGE_ID, update.message.text, message.message_id)

  class_list = CLASS_TO_STUDENTS[update.message.text].values()

  update.message.reply_text('Sending attendance messages...')
  send_attendance_messages(context, class_list)

  return ConversationHandler.END

# Command to cancel ConversationHandler
def cancel(update: Update, _: CallbackContext) -> None:
  update.message.reply_text('Attendance session creation has been canceled.')

# Send messages to all users in usernames
def send_attendance_messages(context: CallbackContext, usernames: list[str]) -> None:
  for username in usernames:
    chat_id = int(redis_db.hget(USERNAME_TO_IDS, username))
    context.bot.send_message(
      chat_id=chat_id,
      text='Mark attendance pls'
    )

########################################
####### COMMANDS FOR THE STUDENT #######
########################################

def mark_attendance(update: Update, context: CallbackContext) -> None:
  classname = redis_db.hget(STUDENTS_TO_CLASS, update.message.from_user.username)
  chat_id = int(redis_db.hget(CLASS_TO_TEACHER, classname))
  message_id = int(redis_db.hget(CLASS_TO_MESSAGE_ID, classname))
  context.bot.edit_message_text(
    text="HAHAHAHA MARKED",
    chat_id=chat_id,
    message_id=message_id
  )
  update.message.reply_text("Attendance marked!")

########################################
############# BOT SETUP ################
########################################

def init_data() -> None:
  with open('classes.json') as f:
    global CLASS_TO_STUDENTS
    CLASS_TO_STUDENTS = json.load(f)
  for classname, students in CLASS_TO_STUDENTS.items():
    for _, student_id in students.items():
      redis_db.hset(STUDENTS_TO_CLASS, student_id, classname)

def main() -> None:
  # Init Redis data
  init_data()

  # Create the Updater and pass it your bot's token.
  updater = Updater('1831856314:AAFja2_HM9Secj55Zqd_2hGkoX-PpX-HFVQ')

  # Get the dispatcher to register handlers
  dispatcher = updater.dispatcher

  # Add command handlers
  dispatcher.add_handler(CommandHandler('start', start))
  dispatcher.add_handler(CommandHandler('mark_attendance', mark_attendance))

  # Add conversation handler with to start attendance session
  conv_handler = ConversationHandler(
      entry_points=[CommandHandler('start_attendance', start_attendance_session)],
      states={
          CLASS: [MessageHandler(Filters.text, class_handler)],
      },
      fallbacks=[CommandHandler('cancel', cancel)],
  )

  dispatcher.add_handler(conv_handler)

  # Start the Bot
  updater.start_polling()

  # Run the bot until you press Ctrl-C or the process receives SIGINT,
  # SIGTERM or SIGABRT. This should be used most of the time, since
  # start_polling() is non-blocking and will stop the bot gracefully.
  updater.idle()


if __name__ == '__main__':
    main()
