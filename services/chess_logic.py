import chess
from typing import Optional

def validate_move(fen: str, move_uci: str) -> bool:
    board = chess.Board(fen)
    move = chess.Move.from_uci(move_uci)
    return move in board.legal_moves

def apply_move(fen: str, move_uci: str) -> str:
    board = chess.Board(fen)
    move = chess.Move.from_uci(move_uci)
    board.push(move)
    return board.fen()

def is_game_over(fen: str) -> bool:
    board = chess.Board(fen)
    return board.is_game_over()

def get_game_result(fen: str) -> Optional[str]:
    board = chess.Board(fen)
    if board.is_checkmate():
        return "black" if board.turn == chess.WHITE else "white"
    if board.is_stalemate() or board.is_insufficient_material() or board.is_fivefold_repetition() or board.is_seventyfive_moves():
        return "draw"
    return None
