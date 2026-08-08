import sqlite3
import json
from uuid import uuid4
from config import DB_FILE
from typing import List, Tuple, Dict

def run_query(sql, params = (), fetch=False) -> List | None:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(sql, params)

    try:
        result = cur.fetchall() if fetch else None
        conn.commit()

        return result
    
    except Exception as e:
        print(f"[ERORR] {__name__}: {e}")
        conn.rollback()
    
    finally:
        conn.close()

def init_db() -> None:
    run_query("""CREATE TABLE IF NOT EXISTS games(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_white_id INTEGER,
                user_black_id INTEGER,
                game_id TEXT UNIQUE,
                won TEXT
    )""")

    run_query("""CREATE TABLE IF NOT EXISTS game_state(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              game_id TEXT,
              next_black INTEGER,
              game_state TEXT,
              FOREIGN KEY (game_id) REFERENCES games(game_id)
    )""")

def create_game(user_white_id: int) -> str:
    game_id = str(uuid4())
    run_query("INSERT INTO games(user_white_id, game_id) VALUES (?, ?)",
              (user_white_id, game_id))
    
    return game_id

def join_game(user_black_id: int, game_id: int) -> bool:
    rows = run_query(
        "SELECT user_black_id FROM games WHERE game_id = ?",
        (game_id,),
        fetch=True
    )

    if not rows or rows[0][0] is not None:
        return False

    run_query(
        "UPDATE games SET user_black_id = ? WHERE game_id = ?",
        (user_black_id, game_id)
    )
    return True

def user_ids(game_id: str) -> Tuple | None:
    rows = run_query(
    "SELECT user_black_id, user_white_id FROM games WHERE game_id = ?",
    (game_id,), fetch=True
    )
    return rows[0] if rows else None

def game_full(game_id: str) -> bool:
    users = user_ids(game_id)

    if not users:
        return False
    return users[0] is not None and users[1] is not None

def create_game_state(game_id: str, next_black: int, game_state: Dict) -> None:
    run_query(
        "INSERT INTO game_state (game_id, next_black, game_state) VALUES (?, ?, ?)", 
        (game_id, next_black, json.dumps(game_state)))

def update_game_state(game_id: str, next_black: int, game_state: Dict) -> None:
    run_query("UPDATE game_state SET next_black = ?, game_state = ? WHERE game_id = ?",
              (next_black, json.dumps(game_state), game_id))

def get_game_state(game_id: str) -> Tuple | None:
    rows = run_query("SELECT next_black, game_state FROM game_state WHERE game_id = ?",
              (game_id,), fetch=True)
    
    if not rows:
        return None
    next_black, game_state_json = rows[0]

    try:
        state = json.loads(game_state_json)
    
    except json.JSONDecodeError:
        print(f"Повреждена запись {game_id}.")
        return None
    
    return next_black, state

def set_winner(game_id: str, winner_color: str) -> None:
    run_query(
        "UPDATE games SET won = ? WHERE game_id = ?",
        (winner_color, game_id),
    )

def get_game_status(game_id: str) -> str | None:
    rows = run_query(
        "SELECT won FROM games WHERE game_id = ?",
        (game_id,), fetch=True,
    )

    return rows[0][0] if rows else None

def get_user_wons(user_id: int) -> int | str:
    rows = run_query(
        "SELECT won, game_id FROM games WHERE ? IN (user_white_id, user_black_id)",
        (user_id,), fetch=True
    )

    if not rows:
        return 0
    wons = 0
    
    for info in rows:
        users_id = user_ids(info[1])
        black_id, white_id = users_id

        if black_id == user_id and info[0] == "black" or white_id == user_id and info[0] == "white":
            wons += 1
    return wons

if __name__ == "__main__":
    import os
    import config

    TEST_DB = str(DB_FILE).replace("games.db", "test_games.db")

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    config.DB_FILE = type(DB_FILE)(TEST_DB)

    init_db()
    # gid = create_game(111)
    # gid = create_game(222)
    # print(gid)
    """print(user_ids("6f2d0312-3747-4982-a103-c36296256879"))
    print(game_full("6f2d0312-3747-4982-a103-c36296256879"))

    print(user_ids("d2373f4d-30ef-4796-b7cd-64ff26fd31ae"))
    print(game_full("d2373f4d-30ef-4796-b7cd-64ff26fd31ae"))

    print(join_game(222, "6f2d0312-3747-4982-a103-c36296256879")"""
    
    # state = {"E2": "white-pawn", "E7": "black-pawn"}
    # create_game_state("f0ef8804-e409-41ba-bcdc-0b8d492e0253", 0, state)

    """state["E4"] = state.pop("E2")
    update_game_state("ed08436a-db35-4474-9f41-1fd572bc43db", 1, state)

    print(get_game_state("ed08436a-db35-4474-9f41-1fd572bc43db")) """
    print(get_user_wons(7606357978))