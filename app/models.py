from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    profile_picture = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), onupdate=func.now())

    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    rating = Column(Integer, default=1200)
    
    # Veze
    sent_friend_requests = relationship("Friend", foreign_keys="Friend.user_id", back_populates="user")
    received_friend_requests = relationship("Friend", foreign_keys="Friend.friend_id", back_populates="friend")
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")
    sent_challenges = relationship("Challenge", foreign_keys="Challenge.challenger_id", back_populates="challenger")
    received_challenges = relationship("Challenge", foreign_keys="Challenge.opponent_id", back_populates="opponent")
    games_as_white = relationship("Game", foreign_keys="Game.white_player_id", back_populates="white_player")
    games_as_black = relationship("Game", foreign_keys="Game.black_player_id", back_populates="black_player")
    tournament_participations = relationship("TournamentParticipant", back_populates="user")

class Friend(Base):
    __tablename__ = "friends"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    friend_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    status = Column(Enum("pending", "accepted", "blocked", name="friend_status"), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id], back_populates="sent_friend_requests")
    friend = relationship("User", foreign_keys=[friend_id], back_populates="received_friend_requests")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")

class Challenge(Base):
    __tablename__ = "challenges"
    id = Column(Integer, primary_key=True, index=True)
    challenger_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    opponent_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum("pending", "accepted", "declined", "expired", name="challenge_status"), default="pending")
    time_control = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    challenger = relationship("User", foreign_keys=[challenger_id], back_populates="sent_challenges")
    opponent = relationship("User", foreign_keys=[opponent_id], back_populates="received_challenges")

class Game(Base):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, index=True)
    white_player_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    black_player_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum("waiting", "active", "finished", "aborted", name="game_status"), default="waiting")
    winner = Column(Enum("white", "black", "draw", name="game_result"), nullable=True)
    current_fen = Column(Text, default="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    time_control = Column(JSON)
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))

    white_player = relationship("User", foreign_keys=[white_player_id], back_populates="games_as_white")
    black_player = relationship("User", foreign_keys=[black_player_id], back_populates="games_as_black")
    moves = relationship("Move", back_populates="game")

class Move(Base):
    __tablename__ = "moves"
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    move_number = Column(Integer)
    move_uci = Column(String(10))
    fen_before = Column(Text)
    fen_after = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    game = relationship("Game", back_populates="moves")

# ========== TURNIRSKI MODELI ==========
class Tournament(Base):
    __tablename__ = "tournaments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # ISPRAVLJENO
    created_by = Column(Integer, ForeignKey("users.id"))
    rounds = Column(Integer, default=1)

    players = relationship("TournamentPlayer", back_populates="tournament")
    matches = relationship("TournamentMatch", back_populates="tournament")

class TournamentPlayer(Base):
    __tablename__ = "tournament_players"
    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    joined_at = Column(DateTime(timezone=True), server_default=func.now())  # ISPRAVLJENO
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    points = Column(Float, default=0.0)

    tournament = relationship("Tournament", back_populates="players")
    user = relationship("User")

class TournamentMatch(Base):
    __tablename__ = "tournament_matches"
    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"))
    round = Column(Integer, nullable=False)
    player1_id = Column(Integer, ForeignKey("users.id"))
    player2_id = Column(Integer, ForeignKey("users.id"))
    result = Column(String, nullable=True)
    played = Column(Boolean, default=False)

    tournament = relationship("Tournament", back_populates="matches")
    player1 = relationship("User", foreign_keys=[player1_id])
    player2 = relationship("User", foreign_keys=[player2_id])

# ========== NOVE KLASE ==========
class FriendRequest(Base):
    __tablename__ = "friend_requests"
    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class GameOpening(Base):
    __tablename__ = "game_openings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    opening_name = Column(String)
    count = Column(Integer, default=0)
    as_white = Column(Boolean)

class TournamentLive(Base):
    __tablename__ = "tournaments_live"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    status = Column(String, default="pending")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    max_players = Column(Integer)
    current_round = Column(Integer, default=0)
    bracket = Column(JSON)

class TournamentParticipantLive(Base):
    __tablename__ = "tournament_participants_live"
    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments_live.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    seed = Column(Integer)
    current_score = Column(Integer, default=0)
