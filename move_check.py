from typing import Tuple, Dict, List

COLUMNS = "ABCDEFGH"
ROWS = "12345678"

COL_INDEX = {col: idx for idx, col in enumerate(COLUMNS)}

def parse_square(square: str) -> Tuple[int] | None: # "A3" -> (0, 3).
    col, row = square[0], square[1]

    if col not in COL_INDEX or row not in ROWS:
        return None
    return COL_INDEX[col], int(row)

def parse_piece(piece_name: str) -> Tuple[str, str]: # "white-pawn" -> ("white", "pawn").
    color, piece = piece_name.split("-")

    return color, piece

def get_path(start: str, end: str) -> List[str]:
    start_col, start_row = parse_square(start)
    end_col, end_row = parse_square(end)

    if end_col == start_col:
        col_step = 0
    else:
        if end_col > start_col:
            col_step = 1
        else:
            col_step = -1

    if end_row == start_row:
        row_step = 0
    else:
        if end_row > start_row:
            row_step = 1
        else:
            row_step = -1
    
    path = list()
    col, row = start_col + col_step, start_row + row_step

    while (col, row) != (end_col, end_row):
        path.append(f"{COLUMNS[col]}{row}")
        col += col_step
        row += row_step
    return path

def is_path_clear(positions: Dict, start: str, end: str) -> bool:
    return all(sq not in positions for sq in get_path(start, end))

def valid_rook(positions: Dict, start: str, end: str) -> bool:
    start_col, start_row = parse_square(start)
    end_col, end_row = parse_square(end)

    if start_col != end_col and start_row != end_row:
        return False
    return is_path_clear(positions, start, end)

def valid_pawn(positions: Dict, start: str, end: str, color: str) -> bool:
    start_col, start_row = parse_square(start) # A3 -> (0, 3).
    end_col, end_row = parse_square(end) # A4 -> (0, 4).
    target = positions.get(end) # None / фигура.

    direction = 1 if color == "white" else -1
    row_diff = end_row - start_row # 1.
    col_diff = abs(end_col - start_col) # 0.

    if col_diff == 0 and row_diff == direction and not target:
        return True

    if col_diff == 0 and row_diff == 2 * direction and not target:
        init_row = 2 if color == "white" else 7
        middle = f"{start[0]}{start_row + direction}"

        if start_row == init_row and middle not in positions:
            return True

    if col_diff == 1 and row_diff == direction and target:
        return True
    return False

def valid_knight(start: str, end: str) -> bool:
    start_col, start_row = parse_square(start)
    end_col, end_row = parse_square(end)

    row_diff = abs(end_row - start_row)
    col_diff = abs(end_col - start_col)

    return (row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2)

def valid_bishop(positions: Dict, start: str, end: str) -> bool:
    start_col, start_row = parse_square(start)
    end_col, end_row = parse_square(end)

    if abs(end_row - start_row) != abs(end_col - start_col):
        return False
    return is_path_clear(positions, start, end)

def valid_queen(positions: Dict, start: str, end: str) -> bool:
    start_col, start_row = parse_square(start)
    end_col, end_row = parse_square(end)

    if start_col == end_col or start_row == end_row: # Перемещение по колонке/строке одинаково(по символу).
        return is_path_clear(positions, start, end)

    if abs(end_row - start_row) == abs(end_col - start_col): # Разница перемещения по строке = разница перемещения по колонке.
        return is_path_clear(positions, start, end)
    return False

def valid_king(start: str, end: str) -> bool:
    start_col, start_row = parse_square(start)
    end_col, end_row = parse_square(end)

    return abs(end_row - start_row) <= 1 and abs(end_col - start_col) <= 1

VALIDATORS = {
    "pawn": lambda pos, start, end, color: valid_pawn(pos, start, end, color),
    "rook": lambda pos, start, end, _: valid_rook(pos, start, end),
    "knight": lambda _, start, end, color: valid_knight(start, end),
    "bishop": lambda pos, start, end, _: valid_bishop(pos, start, end),
    "queen": lambda pos, start, end, _: valid_queen(pos, start, end),
    "king": lambda _, start, end, color: valid_king(start, end)
}

def is_valid_move(positions: Dict, start: str, end: str) -> bool:
    if start == end:
        return False
    
    if not parse_square(start) or not parse_square(end):
        return False
    
    piece_name = positions.get(start)

    if not piece_name:
        return False
    
    color, piece = parse_piece(piece_name)
    target = positions.get(end)

    if target:
        target_color, _ = parse_piece(target)

        if target_color == color:
            return False
    
    validator = VALIDATORS.get(piece)
    return bool(validator and validator(positions, start, end, color))

def find_king(positions: Dict, color: str) -> str | None: # Клетка, на которой находится король.
    king_name = f"{color}-king"

    for square, piece in positions.items():
        if piece == king_name:
            return square
    return None

def is_check(positions: Dict, color: str) -> bool: # Шах / не шах.
    king_square = find_king(positions, color)

    if not king_square:
        return False
    enemy = "white" if color == "black" else "black"

    for square, piece in positions.items():
        piece_color, _ = parse_piece(piece)

        if piece_color == enemy and is_valid_move(positions, square, king_square):
            return True
    return False

def apply_move(positions: Dict, start: str, end: str) -> Dict: # Изменение позиции фигуры на доске.
    new_positions = positions.copy()
    piece = new_positions.pop(start, None)

    if piece:
        new_positions[end] = piece
    return new_positions

def get_legal_moves(positions: Dict, start: str) -> List[str]:
    piece_name = positions.get(start)

    if not piece_name:
        return []
    
    color, _ = parse_piece(piece_name)
    moves = list()

    for col in COLUMNS:
        for row in ROWS:
            target = f"{col}{row}"

            if target == start:
                continue

            if is_valid_move(positions, start, target):
                new_positions = apply_move(positions, start, target)

                if not is_check(new_positions, color):
                    moves.append(start)
    return moves

def _has_legal_moves(positions: Dict, color: str) -> bool:
    for square, piece in positions.items():
        piece_color, _ = parse_piece(piece)

        if piece_color == color and get_legal_moves(positions, square):
            return True
    return False

def is_checkmate(positions: Dict, color: str) -> bool:
    return is_check(positions, color) and not _has_legal_moves(positions, color)

def is_stalemate(positions: Dict, color: str) -> bool:
    return not is_check(positions, color) and not _has_legal_moves(positions, color)

if __name__ == "__main__":
    board = {
        "A8": "black-rook",   "B8": "black-knight", "C8": "black-bishop",
        "D8": "black-queen",  "E8": "black-king",   "F8": "black-bishop",
        "G8": "black-knight", "H8": "black-rook",
        "A7": "black-pawn",   "B7": "black-pawn",   "C7": "black-pawn",
        "D7": "black-pawn",   "E7": "black-pawn",   "F7": "black-pawn",
        "G7": "black-pawn",   "H7": "black-pawn",
        "A2": "white-pawn",   "B2": "white-pawn",   "C2": "white-pawn",
        "D2": "white-pawn",   "E2": "white-pawn",   "F2": "white-pawn",
        "G2": "white-pawn",   "H2": "white-pawn",
        "A1": "white-rook",   "B1": "white-knight", "C1": "white-bishop",
        "D1": "white-queen",  "E1": "white-king",   "F1": "white-bishop",
        "G1": "white-knight", "H1": "white-rook",
    } 
    # ход пешки.
    """print(is_valid_move(board, "E2", "E4"))
    print(is_valid_move(board, "E2", "E3"))
    print(is_valid_move(board, "E2", "E5"))
    print(is_valid_move(board, "E2", "D3"))
    print(is_valid_move(board, "A2", "A4"))"""
    # ход ладьи.
    """print(is_valid_move(board, "A3", "D3"))
    print(is_valid_move(board, "A3", "A7"))
    print(is_valid_move(board, "A3", "A8"))
    print(is_valid_move(board, "A3", "A2"))"""
    # ход коня.
    """print(is_valid_move(board, "B1", "C3"))
    print(is_valid_move(board, "B1", "B3"))
    print(is_valid_move(board, "G2", "G4"))"""
    # ход слона.
    """print(is_valid_move(board, "C1", "E3"))
    print(is_valid_move(board, "C1", "A3"))"""
    # ход ферзя.
    """print(is_valid_move(board, "D1", "D3"))
    print(is_valid_move(board, "D1", "A1"))"""
    # ход короля.
    """print(is_valid_move(board, "E1", "E2"))
    print(is_valid_move(board, "E1", "D1"))"""

    """print(is_check(board, "white"))"""
    
    """print(apply_move(board, "A2", "A4"))
    print(apply_move(board, "A4", "A6"))"""

    fool_mate = {
        "H8": 'black-king',
        "B2": "black-queen",
        "A2": "black-rook",
        "A1": "white-king",
    } 

    stale_mate = {
        "A8": 'black-king',
        "B6": "white-queen",
        "C7": "white-king",
    }

    """from config import BASE_DIR
    from image_manager import render_board
    test = render_board(stale_mate)
    
    test.save(BASE_DIR / "test.png")
    print(is_stalemate(stale_mate, "black"))"""