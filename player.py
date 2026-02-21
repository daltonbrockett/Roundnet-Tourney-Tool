"""
Player module for the Roundnet Tournament Tool.

Defines the Player class which tracks all individual statistics needed
for tournament ranking: wins, losses, points for/against, point differential,
and head-to-head records.
"""

from __future__ import annotations


def validate_score(score_a: int, score_b: int) -> bool:
    """
    Scoring rules:
    - First to 11, win by 2, cap at 15.

    Args:
        score_a: Score of team A.
        score_b: Score of team B.

    Returns:
        True if the score is valid, False otherwise.
    """
    if score_a < 0 or score_b < 0:
        return False

    # Determine winner and loser scores
    winner = max(score_a, score_b)
    loser = min(score_a, score_b)

    # Can't have a tie
    if winner == loser:
        return False

    # Cap is 15
    if winner > 15:
        return False

    # Winner must have at least 11
    if winner < 11:
        return False

    # At the cap: winner is 15, any loser score 13 or 14 is valid
    if winner == 15:
        return loser in (13, 14)

    # Standard win at exactly 11: loser can be 0-9 (any score below 10)
    if winner == 11:
        return loser <= 9

    # Deuce range (12-14): must win by exactly 2
    return winner - loser == 2


class Player:
    """
    Represents a player in the roundnet tournament.

    Tracks name, region, club affiliation, and all statistics needed for
    the tournament ranking system:
    1. Total wins
    2. Head-to-head record (tiebreaker #1)
    3. Point differential / points for / points against (tiebreaker #2)
    """

    def __init__(self, name: str, region: str = "", club: str = "") -> None:
        """
        Initialize a new Player.

        Args:
            name: Player's name.
            region: Player's region (optional).
            club: Team/club affiliation (optional).
        """
        self.name = name
        self.region = region
        self.club = club

        # Cumulative stats
        self.wins: int = 0
        self.losses: int = 0
        self.points_for: int = 0
        self.points_against: int = 0

        # Head-to-head record: {opponent_name: {"wins": int, "losses": int}}
        self.head_to_head: dict[str, dict[str, int]] = {}

    @property
    def point_differential(self) -> int:
        """Calculate point differential (points for minus points against)."""
        return self.points_for - self.points_against

    def record_game(
        self,
        partner: Player,
        opponents: list[Player],
        team_score: int,
        opponent_score: int,
    ) -> None:
        """
        Record the result of a single 2v2 game for this player.

        Updates wins/losses, points for/against, and head-to-head records
        against both opponents.

        Args:
            partner: The player's teammate for this game.
            opponents: List of the two opposing players.
            team_score: This player's team score.
            opponent_score: The opposing team's score.

        Raises:
            ValueError: If the score is invalid or opponents list is not length 2.
        """
        if len(opponents) != 2:
            raise ValueError("There must be exactly 2 opponents in a 2v2 game.")

        if not validate_score(team_score, opponent_score):
            raise ValueError(
                f"Invalid score: {team_score}-{opponent_score}. "
                "Games are to 11 (win by 2, cap at 15)."
            )

        won = team_score > opponent_score

        # Update win/loss record
        if won:
            self.wins += 1
            partner.wins += 1
        else:
            self.losses += 1
            partner.losses += 1

        # Update points
        self.points_for += team_score
        self.points_against += opponent_score
        partner.points_for += team_score
        partner.points_against += opponent_score

        # Update head-to-head against each opponent
        for opponent in opponents:
            if opponent.name not in self.head_to_head:
                self.head_to_head[opponent.name] = {"wins": 0, "losses": 0}
            if opponent.name not in partner.head_to_head:
                partner.head_to_head[opponent.name] = {"wins": 0, "losses": 0}

            if won:
                self.head_to_head[opponent.name]["wins"] += 1
                partner.head_to_head[opponent.name]["wins"] += 1
            else:
                self.head_to_head[opponent.name]["losses"] += 1
                partner.head_to_head[opponent.name]["losses"] += 1

    def get_head_to_head_record(self, opponent: Player) -> tuple[int, int]:
        """
        Get the head-to-head record against a specific opponent.

        Args:
            opponent: The opponent player to look up.

        Returns:
            A tuple of (wins, losses) against the given opponent.
            Returns (0, 0) if they have never played against each other.
        """
        record = self.head_to_head.get(opponent.name, {"wins": 0, "losses": 0})
        return record["wins"], record["losses"]

    def reset_stats(self) -> None:
        """Reset all accumulated statistics to zero."""
        self.wins = 0
        self.losses = 0
        self.points_for = 0
        self.points_against = 0
        self.head_to_head = {}

    def __repr__(self) -> str:
        return (
            f"Player(name='{self.name}', region='{self.region}', club='{self.club}', "
            f"W={self.wins}, L={self.losses}, "
            f"PF={self.points_for}, PA={self.points_against}, "
            f"PD={self.point_differential:+d})"
        )
