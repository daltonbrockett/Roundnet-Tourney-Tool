"""
Tournament scheduler for the Roundnet Tournament Tool.

Generates balanced pool assignments for 16 players across 5 rounds.
Each round has 4 pools of 4 players. Over all 5 rounds, every pair of
players shares a pool exactly once (a resolvable 2-(16,4,1) design).

Within each pool the 3 matchups use the standard partner-rotation:
  Game 1: (0,1) vs (2,3)
  Game 2: (0,2) vs (1,3)
  Game 3: (0,3) vs (1,2)
"""

from __future__ import annotations

# Matchup pairings within a pool of 4 (indices into the pool list)
MATCHUP_PAIRS = [
    ((0, 1), (2, 3)),
    ((0, 2), (1, 3)),
    ((0, 3), (1, 2)),
]

# -----------------------------------------------------------------
# Balanced 16-player design
# -----------------------------------------------------------------
# Arrange players 0-15 on a 4×4 grid:
#
#   0  1  2  3
#   4  5  6  7
#   8  9 10 11
#  12 13 14 15
#
# Round 1: rows
# Round 2: columns
# Rounds 3-5: three distinct diagonals
#
# This guarantees every pair appears in exactly one pool.
# -----------------------------------------------------------------

_DESIGN: list[list[list[int]]] = [
    # Round 1 — rows
    [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]],
    # Round 2 — columns
    [[0, 4, 8, 12], [1, 5, 9, 13], [2, 6, 10, 14], [3, 7, 11, 15]],
    # Round 3 — diagonal set A
    [[0, 5, 10, 15], [1, 4, 11, 14], [2, 7, 8, 13], [3, 6, 9, 12]],
    # Round 4 — diagonal set B
    [[0, 6, 11, 13], [1, 7, 10, 12], [2, 4, 9, 15], [3, 5, 8, 14]],
    # Round 5 — diagonal set C
    [[0, 7, 9, 14], [1, 6, 8, 15], [2, 5, 11, 12], [3, 4, 10, 13]],
]


def generate_rounds(player_names: list[str]) -> list[list[list[str]]]:
    """
    Generate 5 balanced rounds of 4 pools of 4 players.

    Args:
        player_names: List of exactly 16 player names.

    Returns:
        A list of 5 rounds.  Each round is a list of 4 pools.
        Each pool is a list of 4 player-name strings.

    Raises:
        ValueError: If the player list does not contain exactly 16 names.
    """
    if len(player_names) != 16:
        raise ValueError(
            f"Exactly 16 players are required, got {len(player_names)}."
        )

    return [
        [[player_names[i] for i in pool] for pool in round_pools]
        for round_pools in _DESIGN
    ]
