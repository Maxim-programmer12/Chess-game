from telebot import TeleBot
from telebot.types import Message
from pathlib import Path
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image

import database as db
from config import load_bot_token
from image_manager import init_board, render_board, add_endgame_text
from move_check import is_valid_move, is_check, is_checkmate, is_stalemate, apply_move

load_dotenv()

TOKEN = load_bot_token()
BASE_DIR = Path(__file__).resolve().parent

class GameRegistry:
    def __init__(self):
        self._user_to_game = {}
    
    def assign(self, user_id, game_id):
        self._user_to_game[user_id] = game_id
    
    def get(self, user_id):
        return self._user_to_game.get(user_id)
    
    def release(self, *user_ids):
        for uid in user_ids:
            if uid is not None:
                self._user_to_game.pop(uid, None)


bot = TeleBot(token=TOKEN)
db.init_db()
registry = GameRegistry()

def send_board(chat_id: int, board_image: Image, caption: str):
    buf = BytesIO()
    board_image.save(buf, "PNG")
    buf.seek(0)

    bot.send_photo(chat_id, buf, caption=caption)

def send_help(chat_id):
    """Отправляет справочное сообщение."""
    bot.send_message(
        chat_id,
        "Добро пожаловать в Шахматного-бота.\n\n"
        "Используйте команды:\n"
        "/create_game - создать новую игру.\n"
        "/join_game <ID игры> - присоединиться к существующей игре.\n"
        "/move <Откуда> <Куда> - сделать ход (например, /move E2 E4).\n"
        "/leave_game - покинуть текущую игру.\n"
        "/my_wins - количество твоих побед.\n\n"
        "Чтобы пригласить друга, создайте игру и отправьте ему ссылку вида: "
        f"t.me/{bot.get_me().username}?start=<ID_ВАШЕЙ_ИГРЫ>",
    )

@bot.message_handler(commands=["start"])
def start(message: Message):
    args = message.text.split(maxsplit=1)
    game_id = args[1] if len(args) > 1 else None
    user_id = message.from_user.id

    if not game_id:
        send_help(message.chat.id)
        return
    
    if registry.get(user_id):
        bot.send_message(message.chat.id, "Вы уже участвуете в игре."
                         " Завершите или покиньте игру (/leave_game), чтобы присоединиться к новой.")
        return

    players = db.user_ids(game_id)

    if not players:
        bot.send_message(message.chat.id, "Игра с таким ID не найдена!")
        return
    
    black_id, white_id = players

    if white_id == user_id:
        bot.send_message(message.chat.id, "Вы не можете присоединиться к своей же игре!")
        return
    
    if black_id is not None:
        bot.send_message(message.chat.id, "Эта игра уже заполнена!", )
        return
    
    if not db.join_game(user_id, game_id):
        bot.send_message(message.chat.id, "Не удалось присоединиться к игре!")
        return
    
    registry.assign(user_id, game_id)

    if white_id:
        registry.assign(white_id, game_id)
        bot.send_message(white_id, f"К вашей игре присоединился {message.from_user.first_name}. Игра началась!",)
    
    bot.send_message(message.chat.id, f"Вы присоединились к игре. ID: {game_id}.")
    state = db.get_game_state(game_id)

    if not state:
        bot.send_message(message.chat.id, "Ошибка! Не удалось загрузить состояния игры.")
        return
    
    _, positions = state
    board_image = render_board(positions)

    send_board(message.chat.id, board_image, "Игра началась! Ход белых. Вы играете чёрными.")

    if white_id:
        send_board(white_id, board_image, "Игра началась! Ваш ход (белые).")

@bot.message_handler(commands=["create_game"])
def create_game(message: Message):
    user_id = message.from_user.id

    if registry.get(user_id):
        bot.send_message(message.chat.id, "Вы уже в игре! Покиньте игру (/leave_game), чтобы создать новую.")
        return
    
    new_game_id = db.create_game(user_id)

    if not new_game_id:
        bot.send_message(message.chat.id, "Не удалось создать новую игру!",)
        return
    
    registry.assign(user_id, new_game_id)
    board_img, initial_posititons = init_board()

    if not initial_posititons:
        bot.send_message(message.chat.id, "Ошибка! Не удалось начальные позиции.")
        registry.release(user_id)
        return
    
    db.create_game_state(new_game_id, 0, initial_posititons)
    deep_link = f"t.me/{bot.get_me().username}?start={new_game_id}"

    bot.send_message(message.chat.id, 
                     f"Игра создана! <i><b>ID: {new_game_id}</b></i>\n"
                     f"Пригласи второго игрока: <i><b>{deep_link}</b></i>\n\n"
                     "Ожидаем присоединения...",
                     parse_mode="HTML")
    send_board(message.chat.id, board_img, "Эта ваша доска. Вы играете белыми. Ожидайте соперника.")

@bot.message_handler(commands=["join_game"])
def join_game(message: Message):
    args = message.text.split()

    if len(args) < 2:
        bot.send_message(message.chat.id, "Укажите ID игры: /join_game <ID_ИГРЫ>.")
        return

    message.text = f"/start {args[1]}"
    start(message)

@bot.message_handler(commands=["move"])
def move_command(message: Message):
    user_id = message.from_user.id
    game_id = registry.get(user_id)

    if not game_id:
        bot.send_message(message.chat.id, "Вы не в игре! Создайте игру (/create_game) или присоединитесь к ней (/join_game).")
        return

    if db.get_game_status(game_id):
        bot.send_message(message.chat.id, "Игра уже завершена!")
        return
    
    players = db.user_ids(game_id)

    if not players or None in players:
        bot.send_message(message.chat.id, "Не хватает игрока! Дождитесь его.")
        return
    
    black_id, white_id = players
    state = db.get_game_state(game_id)

    if not state:
        bot.send_message(message.chat.id, "Ошибка состояния!")
        return
    
    is_black_turn, positions = state
    current_color = "black" if is_black_turn else "white"
    expected_player = black_id if is_black_turn else white_id

    if user_id != expected_player:
        bot.send_message(message.chat.id, f"Сейчас не ваш ход! Ждите {current_color}...")
        return

    parts = message.text.split()

    if len(parts) != 3:
        bot.send_message(message.chat.id, "Неверный формат! Надо по шаблону: /move <Откуда> <Куда> (например, /move e2 e4).")
        return
    
    move_from = parts[1].upper()
    move_to = parts[2].upper()

    piece = positions.get(move_from)

    if not piece:
        bot.send_message(message.chat.id, f"На клетке {piece} нет фигуры!")
        return
    
    if current_color not in piece:
        bot.send_message(message.chat.id, f"Это фигура противника! Ваш цвет: {current_color}")
        return
    
    if not is_valid_move(positions, move_from, move_to):
        bot.send_message(message.chat.id, f"Недопустимый ход: {move_from} -> {move_to}")
        return
    
    new_positions = apply_move(positions, move_from, move_to)

    if is_check(new_positions, current_color):
        bot.send_message(message.chat.id, "Нелегальный ход! Ваш король под шахом.")
        return
    
    next_turn = 1 if current_color == "white" else 0
    db.update_game_state(game_id, next_turn, new_positions)
 
    opponent_color = "black" if current_color == "white" else "white"
    board_img = render_board(new_positions)
 
    my_caption = f"Ваш ход: {move_from} -> {move_to}."
    opponent_caption = f"Ход противника ({current_color}): {move_from} -> {move_to}."
    game_over = False
 
    if is_checkmate(new_positions, opponent_color):
        text = f"Мат! {current_color.capitalize()} выигрывают."
        my_caption = text
        opponent_caption = text

        board_img = add_endgame_text(board_img, text)
        db.set_winner(game_id, current_color)

        game_over = True
 
    elif is_stalemate(new_positions, opponent_color):
        text = "Пат! (=ничья)."
        my_caption = text
        opponent_caption = text

        board_img = add_endgame_text(board_img, text)
        db.set_winner(game_id, "draw")

        game_over = True
 
    elif is_check(new_positions, opponent_color):
        alert = f"Шах игроку {opponent_color}!"
        my_caption += alert
        opponent_caption += alert
        opponent_id = black_id if opponent_color == "white" else white_id

        if opponent_id:
            bot.send_message(opponent_id, "Вам объявлен шах!")
 
    if white_id:
        caption = my_caption if user_id == white_id else opponent_caption
        send_board(white_id, board_img, caption)

    if black_id:
        caption = my_caption if user_id == black_id else opponent_caption
        send_board(black_id, board_img, caption)      
 
    if game_over:
        registry.release(white_id, black_id)

@bot.message_handler(commands=["leave_game"])
def leave_game_command(message):
    user_id = message.from_user.id
    game_id = registry.get(user_id)
 
    if not game_id:
        bot.send_message(user_id, "Вы не в игре!")
        return
 
    registry.release(user_id)
    bot.send_message(user_id, f"Вы покинули игру {game_id}.")
 
    players = db.user_ids(game_id)
    if not players or None in players:
        return
 
    black_id, white_id = players
    other_user = white_id if user_id == black_id else black_id
 
    if other_user and db.get_game_status(game_id) is None:
        winner_color = "black" if user_id == white_id else "white"
        db.set_winner(game_id, winner_color)

        bot.send_message(other_user,
            f"Игрок {message.from_user.first_name} покинул игру. Вам присуждена победа!",
        )
        registry.release(other_user)

@bot.message_handler(commands=["my_wins"])
def get_wins(message: Message):
    user_wons = db.get_user_wons(message.from_user.id)

    bot.send_message(message.chat.id, f"🧍 {message.from_user.first_name}, у тебя <i><b>{user_wons} побед(-ы, -а)</b></i> 🏆.",
                     parse_mode="HTML")

bot.infinity_polling(skip_pending=True)