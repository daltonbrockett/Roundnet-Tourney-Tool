"""
Flask web application for the Roundnet Tournament Tool.

Provides a UI for managing players and viewing the leaderboard.
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from player import Player, validate_score
from scheduler import generate_rounds, MATCHUP_PAIRS

app = Flask(__name__)
app.secret_key = "roundnet-tourney-dev-key"

# In-memory storage
players: dict[str, Player] = {}

# Tournament state
tournament_rounds: list[list[list[str]]] = []   # 5 rounds x 4 pools x 4 names
round_scores: dict[int, list[dict]] = {}         # round_idx -> list of game dicts


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


@app.route("/players/<name>/edit", methods=["POST"])
def edit_player(name):
    """Edit a player's name, region, or club."""
    if name not in players:
        flash(f"Player '{name}' not found.", "error")
        return redirect(url_for("players_page"))

    new_name = request.form.get("name", "").strip()
    new_region = request.form.get("region", "").strip()
    new_club = request.form.get("club", "").strip()

    if not new_name:
        flash("Player name is required.", "error")
        return redirect(url_for("players_page"))

    player = players[name]

    # If the name changed, re-key the dict and update head-to-head refs
    if new_name != name:
        if new_name in players:
            flash(f"Player '{new_name}' already exists.", "error")
            return redirect(url_for("players_page"))

        # Update head-to-head records in other players
        for p in players.values():
            if name in p.head_to_head:
                p.head_to_head[new_name] = p.head_to_head.pop(name)

        # Update game history in round_scores
        for ri in round_scores:
            for game in round_scores[ri]:
                game["team_a"] = [new_name if n == name else n for n in game["team_a"]]
                game["team_b"] = [new_name if n == name else n for n in game["team_b"]]

        # Update tournament round pools
        for rnd in tournament_rounds:
            for pool in rnd:
                for i, n in enumerate(pool):
                    if n == name:
                        pool[i] = new_name

        # Re-key in the players dict
        del players[name]
        player.name = new_name
        players[new_name] = player

    player.region = new_region
    player.club = new_club
    flash(f"Updated {new_name}.", "success")
    return redirect(url_for("players_page"))


# ── helpers ──────────────────────────────────────────────────────

def recalculate_all_stats():
    """Rebuild every player's stats from the stored round_scores."""
    for p in players.values():
        p.reset_stats()

    for ri in sorted(round_scores):
        for game in round_scores[ri]:
            p_a1 = players[game["team_a"][0]]
            p_a2 = players[game["team_a"][1]]
            p_b1 = players[game["team_b"][0]]
            p_b2 = players[game["team_b"][1]]
            score_a = game["score_a"]
            score_b = game["score_b"]

            p_a1.record_game(
                partner=p_a2, opponents=[p_b1, p_b2],
                team_score=score_a, opponent_score=score_b,
            )
            p_b1.record_game(
                partner=p_b2, opponents=[p_a1, p_a2],
                team_score=score_b, opponent_score=score_a,
            )


# ── tournament management ────────────────────────────────────────

@app.route("/tournament/generate", methods=["POST"])
def generate_tournament():
    """Generate balanced rounds for 16 registered players."""
    if len(players) != 16:
        flash("Exactly 16 players are required to generate the tournament.", "error")
        return redirect(url_for("scores_page"))

    global tournament_rounds, round_scores
    player_names = sorted(players.keys(), key=str.lower)
    tournament_rounds = generate_rounds(player_names)
    round_scores = {}
    for p in players.values():
        p.reset_stats()
    flash("Tournament generated — 5 rounds are ready!", "success")
    return redirect(url_for("scores_page"))


@app.route("/tournament/reset", methods=["POST"])
def reset_tournament():
    """Clear all rounds and scores."""
    global tournament_rounds, round_scores
    tournament_rounds = []
    round_scores = {}
    for p in players.values():
        p.reset_stats()
    flash("Tournament has been reset.", "success")
    return redirect(url_for("scores_page"))


# ── scores pages ─────────────────────────────────────────────────

@app.route("/scores")
def scores_page():
    """Rounds overview — shows all rounds with completion status."""
    rounds_info = []
    for ri, pools in enumerate(tournament_rounds):
        rounds_info.append({
            "index": ri,
            "pools": pools,
            "completed": ri in round_scores,
        })
    return render_template(
        "scores.html",
        players=list(players.values()),
        rounds=rounds_info,
        tournament_generated=bool(tournament_rounds),
    )


@app.route("/scores/<int:round_idx>", methods=["GET", "POST"])
def round_detail(round_idx):
    """Enter / edit scores for a single round."""
    if not tournament_rounds or round_idx < 0 or round_idx >= len(tournament_rounds):
        flash("Invalid round.", "error")
        return redirect(url_for("scores_page"))

    pools = tournament_rounds[round_idx]

    if request.method == "POST":
        all_valid = True
        new_games: list[dict] = []

        for pi, pool in enumerate(pools):
            for gi, (team_a_idx, team_b_idx) in enumerate(MATCHUP_PAIRS):
                field_a = f"pool_{pi}_game_{gi}_score_a"
                field_b = f"pool_{pi}_game_{gi}_score_b"
                try:
                    score_a = int(request.form.get(field_a, "0"))
                    score_b = int(request.form.get(field_b, "0"))
                except ValueError:
                    flash(f"Pool {pi+1}, Game {gi+1}: Scores must be numbers.", "error")
                    all_valid = False
                    continue

                if not validate_score(score_a, score_b):
                    flash(
                        f"Pool {pi+1}, Game {gi+1}: Invalid score {score_a}-{score_b}. "
                        "Games are to 11 (win by 2, cap at 15).",
                        "error",
                    )
                    all_valid = False
                    continue

                new_games.append({
                    "team_a": [pool[team_a_idx[0]], pool[team_a_idx[1]]],
                    "team_b": [pool[team_b_idx[0]], pool[team_b_idx[1]]],
                    "score_a": score_a,
                    "score_b": score_b,
                })

        if not all_valid:
            existing = round_scores.get(round_idx, [])
            return render_template(
                "round_detail.html",
                round_idx=round_idx,
                pools=pools,
                matchup_pairs=MATCHUP_PAIRS,
                existing_scores=existing,
            )

        round_scores[round_idx] = new_games
        recalculate_all_stats()
        flash(f"Round {round_idx + 1} scores saved!", "success")
        return redirect(url_for("scores_page"))

    existing = round_scores.get(round_idx, [])
    return render_template(
        "round_detail.html",
        round_idx=round_idx,
        pools=pools,
        matchup_pairs=MATCHUP_PAIRS,
        existing_scores=existing,
    )


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
