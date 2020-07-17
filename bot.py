"""
Simple Bot to reply to Telegram messages.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

from uuid import uuid4
import json
from time import time
from pymongo.collection import Collection
import pymongo


from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, \
    InputTextMessageContent, ParseMode, CallbackQuery
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, InlineQueryHandler, CallbackQueryHandler

from analyzer import Analyzer

COOLDOWN = 11
schedule_numbers = json.load(open('schedule_numbers.json', 'r', encoding='utf8'))
schedules = list(schedule_numbers.keys())
analyzers = {schedule: None for schedule in schedules}


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    user_id = update.message.chat.id
    users.insert_one({'state': 'start', 'user_id': user_id, 'schedule': None, 'name': None, 'last_update_time': None})
    reply_keyboard = [[InlineKeyboardButton('Выбрать', switch_inline_query_current_chat='Начните писать название: ')]]
    update.message.reply_text('Здравствуйте! Пожалуйста, выберите направление, которое вы хотите отслеживать.',
                              reply_markup=InlineKeyboardMarkup(reply_keyboard, resize_keyboard=True))


def set_schedule(update, context):
    user_id = update.message.chat.id
    schedule = update.message.text
    update.message.reply_text('Подождите, идёт обработка запроса...')
    if analyzers.get(schedule) is None:
        analyzers[schedule]: Analyzer = Analyzer(schedule)
    analyzers[schedule].update_data()

    # users[user_id]['state'] = 'schedule_set'
    users.find_one_and_update({'user_id': user_id}, {'$set': {'state': 'schedule_set'}})
    # users[user_id]['schedule'] = schedule
    users.find_one_and_update({'user_id': user_id}, {'$set': {'schedule': schedule}})
    # users[user_id]['last_update_time'] = -10
    users.find_one_and_update({'user_id': user_id}, {'$set': {'last_update_time': -10}})

    reply_keyboard = [[InlineKeyboardButton('🔄 Обновить', callback_data='update_schedule')],
                      [InlineKeyboardButton('🥇 Определить место в рейтинге', callback_data='set_enrollee')],
                      [InlineKeyboardButton('🖊 Выбрать другое направление',
                                            switch_inline_query_current_chat='Начните писать название: ')]]
    update.message.reply_text(analyzers[schedule].formatted_result(),
                              reply_markup=InlineKeyboardMarkup(reply_keyboard),
                              parse_mode=ParseMode.HTML)


def update_schedule(update, context):
    query: CallbackQuery = update.callback_query
    user_id = query.message.chat.id
    current_user = users.find_one({'user_id': user_id})
    if time() - current_user['last_update_time'] > COOLDOWN:
        users.find_one_and_update({'user_id': user_id}, {'$set': {'last_update_time': time()}})
        user_schedule = current_user['schedule']
        if analyzers.get(user_schedule) is None:
            analyzers[user_schedule] = Analyzer(user_schedule)
        analyzers[user_schedule].update_data()
        message = analyzers[user_schedule].formatted_result()
        keyboard_inline = [[InlineKeyboardButton('🔄 Обновить', callback_data='update_schedule')],
                           [InlineKeyboardButton('🥇 Определить место в рейтинге', callback_data='set_enrollee')],
                           [InlineKeyboardButton('🖊 Выбрать другое направление',
                                                 switch_inline_query_current_chat='Начните писать название: ')]]
        query.edit_message_text(text=message, parse_mode=ParseMode.HTML,
                                reply_markup=InlineKeyboardMarkup(keyboard_inline))
        query.answer(text='Информация обновлена')
    else:
        query.answer(text=f"Не так часто, пожалуйста! Попробуйте снова через "
                          f"{int(COOLDOWN - time() + current_user['last_update_time']) + 1}")


def inlinequery(update, context):
    results = []
    query: str = update.inline_query.query
    user_id = update.inline_query.from_user.id
    if query.startswith('Начните писать название: '):
        query = query.replace('Начните писать название: ', '').lower()
        for schedule in schedules:
            if query in schedule.lower() or query == 'все':
                results.append(InlineQueryResultArticle(
                    id=uuid4(),
                    title=schedule,
                    input_message_content=InputTextMessageContent(schedule)))
    elif query.startswith('Начните писать ФИО: '):
        query = query.replace('Начните писать ФИО: ', '').lower()
        current_user = users.find_one(user_id)
        if current_user.get('schedule') is None:
            update.inline_query.answer([InlineQueryResultArticle(
                    id=uuid4(),
                    title='Сначала выберите направление!',
                    input_message_content=InputTextMessageContent('Сначала выберите направление!'))])
            return
        schedule = current_user['schedule']
        if analyzers.get(schedule) is None:
            analyzers[schedule] = Analyzer(schedule)
        for enrollee in analyzers[schedule].enrollee_list():
            if query in enrollee.lower() or query == 'все':
                results.append(InlineQueryResultArticle(
                    id=uuid4(),
                    title=enrollee,
                    input_message_content=InputTextMessageContent('Абитуриент: ' + enrollee)))

    update.inline_query.answer(results[:20])


def help_command(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Здравствуйте! Этот бот поможет вам отследить поступление в университет ИТМО. '
                              'Он создан независимым разработчиком, не имеющим никакого отношения к администрации'
                              ' университета, а это значит, что администрация не несёт ответственности за правильность'
                              ' предоставленных данных. Однако в моих интересах делать их как можно более достоверными'
                              ' и полными, поэтому я беру их с '
                              '<a href="https://abit.itmo.ru">официального сайта для абитуриентов</a>.\n'
                              ' Интерфейс прост и интуитивно понятен. Со всеми проблемами, предложениями'
                              ' или вопросами пишите @rainbow_cat13', parse_mode=ParseMode.HTML)


def set_enrollee(update, context):
    reply_keyboard = [[InlineKeyboardButton('Найти', switch_inline_query_current_chat='Начните писать ФИО: ')]]
    context.bot.send_message(update.callback_query.message.chat.id,
                             'Найдите себя или друга в списке', reply_markup=InlineKeyboardMarkup(reply_keyboard))


def count_rating(update, context):
    enrollee = update.message.text.replace('Абитуриент: ', '')
    current_user = users.find_one(update.message.chat.id)
    if current_user.get('schedule') is None:
        update.message.reply_text('Сначала выберите направление!')
        return
    schedule = current_user['schedule']
    place, condition = analyzers[schedule].count_enrollee_rating(enrollee)
    static_string = f'📊 Вы занимаете {place}-е место в списке поступающих {condition}'
    if condition == 'по общему конкурсу':
        static_string += ' (учитывая людей с БВИ впереди вас)'
    static_string += '.\n'
    places_amount = analyzers[schedule].get_places_amount()
    if condition in ['по общему конкурсу', 'без вступительных испытаний']:
        enr_amount = places_amount['Всего бюджет'] - \
                     places_amount['По особой квоте'] - \
                     places_amount['По целевой квоте']
    elif condition == 'на бюджетное место в пределах особой квоты':
        enr_amount = places_amount['По особой квоте']
    elif condition == 'на бюджетное место в пределах целевой квоты':
        enr_amount = places_amount['По целевой квоте']
    else:
        enr_amount = places_amount['Всего контракт']
    if enr_amount >= place:
        static_string += '✅ Данные последнего обновления показывают, что вы можете поступить!'
    else:
        static_string += '⛔ К сожалению, вы не проходите по конкурсу. ' \
                         'Возможно, стоит попробовать иной способ поступления?'
    if condition == 'без вступительных испытаний':
        update.message.reply_text('📊 Вы поступаете без вступительных испытаний.\n'
                                  '✅ Данные последнего обновления показывают, что вы можете поступить!')
    else:
        update.message.reply_text(static_string)


if __name__ == '__main__':
    """Start the bot."""

    # setting up database
    mongo = pymongo.MongoClient('mongodb://localhost:27017/')
    db = mongo['hse-abit']
    users: Collection = db['users']

    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater("1221284343:AAGeQdXqp67UyF6gSHw7NbNJHRbdAdjOoXQ", use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("restart", start))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.regex(f'^({"|".join(schedules)})$'), set_schedule))
    dp.add_handler(MessageHandler(Filters.regex(f'^Абитуриент: .*$'), count_rating))
    dp.add_handler(InlineQueryHandler(inlinequery))

    # on callbacks
    dp.add_handler(CallbackQueryHandler(callback=update_schedule, pattern='^update_schedule$'))
    dp.add_handler(CallbackQueryHandler(callback=set_enrollee, pattern='^set_enrollee$'))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
