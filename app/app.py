from aiogram import Bot, Dispatcher, executor, types
from random import randint
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
import redis

API_TOKEN = ''

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    greeting = 'Я бот для игры в Иике-Баану. Мои команды:\n'
    greeting += '/start - старт\n'
    greeting += '/help - справка\n'
    greeting += '/rules - правила игры\n'
    greeting += '/newgame - начать новую игру\n'
    greeting += '/stat - посмотреть стаститику\n'
    greeting += '/reset - сбросить статистику\n'

    if message.text == '/start':
        r = redis.Redis(host='redis', port=6379)
        stat = [0, 0]
        r.set('__stat__' + str(message.chat.id), bytes(stat))

    await message.answer(greeting)


@dp.message_handler(commands=['newgame'])
async def start_new_game(message: types.Message):
    button_1 = InlineKeyboardButton(text='Конечно, я!', callback_data='move_user')
    button_2 = InlineKeyboardButton(text='Ты ходи', callback_data='move_bot')

    kb = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(button_1, button_2)

    generate_configuration(message.chat.id)
    text = print_config(message.chat.id)

    await message.answer(
        text + 'Кто будет '
               'ходить '
               'первым?',
        reply_markup=kb)


@dp.message_handler(commands=['stat'])
async def view_stat(message: types.Message):
    r = redis.Redis(host='redis', port=6379)
    stat = list(r.get('__stat__' + str(message.chat.id)))

    text = 'Сыграно ' + str(stat[1]) + ' игр\n'
    text += 'Выиграно ' + str(stat[0]) + ' игр\n'

    await message.answer(text)


@dp.message_handler(commands=['reset'])
async def reset_stat(message: types.Message):
    r = redis.Redis(host='redis', port=6379)
    r.set('__stat__' + str(message.chat.id), bytes([0, 0]))


@dp.message_handler(commands=['rules'])
async def get_rules(message: types.Message):
    await message.answer(
        'Целью Иике-Бааны является составление собственно Иике-Бааны из 15 цветков: по 3 каждого из цветов - красного, зелёного, '
        'синего, фиолетового, жёлтого. Игроки по очереди добавляют в Иике-Баану от 1 до 3 цветков одного цвета ('
        'нельзя, чтобы их стало больше 3). Побеждает тот, кто добавит свой цветок последним. Вы можете выбирать кому '
        'ходить первым.')


@dp.callback_query_handler(lambda c: c.data.startswith('move'))
async def move_handler(callback_query: types.CallbackQuery):
    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=None
    )

    if callback_query.data == 'move_user':
        await user_move(callback_query.from_user.id)
    else:
        await bot_move(callback_query.from_user.id)


async def user_move(user_id):
    r = redis.Redis(host='redis', port=6379)
    config = list(r.get(user_id))

    colors = ['красного', 'зелёного', 'синего', 'фиолетового', 'жёлтого']
    kb = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    for i in range(5):
        if config[i] < 3:
            button = InlineKeyboardButton(text=colors[i], callback_data='add_color' + str(i))
            kb.add(button)

    await bot.send_message(user_id, text='Цветков какого цвета Вы хотите добавить?', reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith('add_color'))
async def add_color_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    r = redis.Redis(host='redis', port=6379)
    config = list(r.get(user_id))

    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=None
    )

    count_kb = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    index = int(callback_query.data[-1])

    r.set('__current_color__' + str(user_id), index)

    for i in range(3 - config[index]):
        button = InlineKeyboardButton(text=str(i + 1), callback_data='add_count' + str(i + 1))
        count_kb.add(button)

    await bot.send_message(user_id, text='Сколько цветков Вы хотите добавить?', reply_markup=count_kb)


@dp.callback_query_handler(lambda c: c.data.startswith('add_count'))
async def add_count_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    r = redis.Redis(host='redis', port=6379)
    config = list(r.get(user_id))

    await bot.edit_message_reply_markup(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=None
    )

    count = int(callback_query.data[-1])
    config[int(r.get('__current_color__' + str(user_id)))] += count
    r.set(user_id, bytes(config))

    await bot.send_message(user_id, text='Отлично!')
    await bot.send_message(user_id, print_config(user_id))
    await bot_move(user_id)


async def bot_move(user_id):
    r = redis.Redis(host='redis', port=6379)
    config = list(r.get(user_id))

    for i in range(5):
        if config[i] < 3:
            break
    else:
        await bot.send_message(user_id, text='Хм, кажется я проиграл. Поздравляю!')
        stat = list(r.get('__stat__' + str(user_id)))
        stat[0] += 1
        stat[1] += 1
        r.set('__stat__' + str(user_id), bytes(stat))
        return

    xor = 0
    for i in range(5):
        xor ^= (3 - config[i])

    colors = ['красных', 'зелёных', 'синих', 'фиолетовых', 'жёлтых']
    flag = False

    for i in range(5):
        for count in range(1, 4 - config[i]):
            if xor == 0 or (xor ^ config[i] ^ (config[i] + count) == 0):
                config[i] += count
                await bot.send_message(user_id, text='Добавлю-ка я ' + colors[i] + ' цветков')
                await bot.send_message(user_id, text='Думаю, ' + str(count) + ' будет в самый раз')
                flag = True
                break
        if flag:
            break

    for i in range(5):
        if config[i] < 3:
            break
    else:
        await bot.send_message(user_id, text='Ура, я победил!')
        stat = list(r.get('__stat__' + str(user_id)))
        stat[1] += 1
        r.set('__stat__' + str(user_id), bytes(stat))
        return

    r.set(user_id, bytes(config))
    await bot.send_message(user_id, text=print_config(user_id))
    await user_move(user_id)


def generate_configuration(user_id):
    r = redis.Redis(host='redis', port=6379)

    config = []

    while True:
        for i in range(5):
            config.append(randint(0, 3))

        if sum(config) > 10:
            config.clear()
            continue
        break

    r.set(user_id, bytes(config))


def print_config(user_id):
    r = redis.Redis(host='redis', port=6379)
    config = list(r.get(user_id))
    result = 'Итак, сейчас в Иике-Баане следующее количество цветков:\n'

    colors = ['красных', 'зелёных', 'синих', 'фиолетовых', 'жёлтых']

    for i in range(5):
        result += colors[i] + ' - ' + str(config[i]) + '\n'

    return result


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
