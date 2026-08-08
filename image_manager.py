import json
from functools import lru_cache
from typing import Tuple, Dict, Iterable
from PIL import Image, ImageDraw, ImageFont
from config import ASSESTS_DIR, INIT_POSITIONS, BASE_DIR

OFFSET = 35
CELL_SIZE = 60
BOARD_FILE = ASSESTS_DIR / "board.png"
FONT_FILE = BASE_DIR / "Roboto-VariableFont_wdth,wght.ttf"

LETTER_TO_INDEX = {chr(65 + i): i for i in range(8)}

def translate_position(position : str) -> Tuple[int, int]: # a2.
    column = LETTER_TO_INDEX[position[0].upper()] # a -> A -> 0.
    row = 8 - int(position[1]) # 8 - 2.

    return column, row

def _to_pixes(grid_coords : Tuple[int, int]) -> Tuple[int, int]:
    x, y = grid_coords

    return OFFSET + x * CELL_SIZE, OFFSET + y * CELL_SIZE

@lru_cache(maxsize=None)
def _load_board_template() -> Image.Image:
    return Image.open(BOARD_FILE).convert("RGBA")

@lru_cache(maxsize=None)
def _load_figure(name : str) -> Image.Image:
    figure_path = ASSESTS_DIR / f"{name}.png"

    return Image.open(figure_path).convert("RGBA")

def iter_position(game_state : Dict[str, str]) -> Iterable[Tuple[str, str]]:
    return game_state.items()

def render_board(game_state : Dict[str, str]) -> Image.Image:
    board = _load_board_template().copy()

    for position, figure_name in iter_position(game_state):
        try:
            figure_img = _load_figure(figure_name)

        except FileNotFoundError:
            print(f"[x] Erorr: изображение {figure_name} не найдено!")
            continue

        pixel_position = _to_pixes(translate_position(position))
        board.paste(figure_img, pixel_position, figure_img)
    return board

def load_initial_state() -> Dict[str, str]:
    try:
        with INIT_POSITIONS.open("r", encoding="utf-8") as file:
            return json.load(file)
        
    except FileNotFoundError:
        print("[x] Erorr: файл не найден!")

    except json.JSONDecodeError:
        print("[x] Erorr: неккоректный json-файл!")
    return {}

def init_board() -> Tuple[Image.Image, Dict[str, str]]:
    init_state = load_initial_state()

    return render_board(init_state), init_state

def add_endgame_text(board_image : Image.Image, text : str) -> Image.Image: 
    draw = ImageDraw.Draw(board_image)

    try:
        font = ImageFont.truetype(FONT_FILE, 30)

    except IOError:
        font = ImageFont.load_default()
 
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
 
    board_width, board_height = board_image.size
    text_x_position = (board_width - text_width) / 2
    text_y_position = (board_height - text_height) / 2
 
    rect_padding = 10
    rect_x0 = text_x_position - rect_padding
    rect_y0 = text_y_position - rect_padding
    rect_x1 = text_x_position + text_width + rect_padding
    rect_y1 = text_y_position + text_height + rect_padding
    draw.rectangle([rect_x0, rect_y0, rect_x1, rect_y1], fill=(255, 255, 255, 180))
 
    draw.text((text_x_position, text_y_position), text, fill="black", font=font)

    return board_image

if __name__ == "__main__":
    # print(_to_pixes(translate_position("A4")))

    board, pos = init_board()
    board = add_endgame_text(board, "Ты проиграл!")
    board.save(BASE_DIR / "test.png")