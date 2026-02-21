"""
Flask web application for the Roundnet Tournament Tool.

Provides a UI for managing players and viewing the leaderboard.
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from player import Player, validate_score

app = Flask(__name__)
app.secret_key = "roundnet-tourney-dev-key"

# In-memory storage
players: dict[str, Player] = {}
games: list[dict] = []  # Game history for auditing

# The 3 matchup pairings for a pool of 4 (indices into the pool list)
MATCHUP_PAIRS = [
    ((0, 1), (2, 3)),
    ((0, 2), (1, 3)),
    ((0, 3), (1, 2)),
]


@app.route("/")
def index():
    """Redirect to the players page."""
    return redirect(url_for("players_page"))


@app.route("/players", methods=["GET", "POST"])
def players_page():
    """Show player list and handle adding new players."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        region = request.form.get("region", "").strip()
        club = request.form.get("club", "").strip()

        if not name:
            flash("Player name is required.", "error")
        elif name in players:
            flash(f"Player '{name}' already exists.", "error")
        else:
            players[name] = Player(name, region, club)
            flash(f"Added {name}!", "success")
            return redirect(url_for("players_page"))

    player_list = sorted(players.values(), key=lambda p: p.name.lower())
    return render_template("players.html", players=player_list)


@app.route("/players/<name>/delete", methods=["POST"])
def delete_player(name):
    """Remove a player."""
    if name in players:
        del players[name]
        flash(f"Removed {name}.", "success")
    else:
        flash(f"Player '{name}' not found.", "error")
    return redirect(url_for("players_page"))


@app.route("/scores", methods=["GET", "POST"])
def scores_page():
    """Score entry: select 4 pool players, enter scores for 3 games."""
    player_list = sorted(players.values(), key=lambda p: p.name.lower())

    if request.method == "POST":
        # Collect the 4 selected player names
        pool_names = [request.form.get(f"player_{i}", "").strip() for i in range(4)]

        # Validate pool selection
        if any(not n for n in pool_names):
            flash("Please select all 4 pool players.", "error")
            return render_template("scores.html", players=player_list,
                                   selected=pool_names, show_matchups=False)

        if len(set(pool_names)) < 4:
            flash("All 4 players must be different.", "error")
            return render_template("scores.html", players=player_list,
                                   selected=pool_names, show_matchups=False)

        for n in pool_names:
            if n not in players:
                flash(f"Player '{n}' not found.", "error")
                return render_template("scores.html", players=player_list,
                                       selected=pool_names, show_matchups=False)

        pool = [players[n] for n in pool_names]

        # Validate and record each game
        all_valid = True
        game_scores = []
        for idx, (team_a_idx, team_b_idx) in enumerate(MATCHUP_PAIRS):
            try:
                score_a = int(request.form.get(f"game_{idx}_score_a", "0"))
                score_b = int(request.form.get(f"game_{idx}_score_b", "0"))
            except ValueError:
                flash(f"Game {idx + 1}: Scores must be numbers.", "error")
                all_valid = False
                continue

            if not validate_score(score_a, score_b):
                flash(
                    f"Game {idx + 1}: Invalid score {score_a}-{score_b}. "
                    "Games are to 11 (win by 2, cap at 15).",
                    "error",
                )
                all_valid = False
                continue

            game_scores.append((idx, team_a_idx, team_b_idx, score_a, score_b))

        if not all_valid:
            return render_template("scores.html", players=player_list,
                                   selected=pool_names, show_matchups=True)

        # All valid — record games
        for idx, team_a_idx, team_b_idx, score_a, score_b in game_scores:
            p_a1 = pool[team_a_idx[0]]
            p_a2 = pool[team_a_idx[1]]
            p_b1 = pool[team_b_idx[0]]
            p_b2 = pool[team_b_idx[1]]

            # record_game updates self + partner
            p_a1.record_game(
                partner=p_a2,
                opponents=[p_b1, p_b2],
                team_score=score_a,
                opponent_score=score_b,
            )
            # Record from opponent side
            p_b1.record_game(
                partner=p_b2,
                opponents=[p_a1, p_a2],
                team_score=score_b,
                opponent_score=score_a,
            )

            games.append({
                "team_a": [p_a1.name, p_a2.name],
                "team_b": [p_b1.name, p_b2.name],
                "score_a": score_a,
                "score_b": score_b,
            })

        flash("All 3 games recorded!", "success")
        return redirect(url_for("leaderboard"))

    return render_template("scores.html", players=player_list,
                           selected=None, show_matchups=False)


@app.route("/leaderboard")
def leaderboard():
    """Show the leaderboard sorted by ranking criteria."""
    ranked = sorted(
        players.values(),
        key=lambda p: (p.wins, p.point_differential, p.points_for),
        reverse=True,
    )
    return render_template("leaderboard.html", players=ranked)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
