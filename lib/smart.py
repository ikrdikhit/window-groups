"""
lib/smart.py — Smart group analysis and auto-suggestion.
No external ML deps — pure stdlib heuristics.
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from . import config
from . import ui


def smart_menu():
    options = [
        "🔍  Suggest groups from usage patterns",
        "📊  Most-launched apps",
        "🕑  Recent sessions (last 10)",
        "💡  Auto-create a smart group",
        "🗓️   Time-of-day analysis",
    ]
    sel = ui.prompt(
        "Smart Groups",
        options,
        message="Pattern analysis of your launch history — no data leaves your machine",
    )
    if not sel:
        return

    history = config.load_history()
    launches  = history.get("launches", [])
    co        = history.get("cooccurrence", {})

    if "Suggest" in sel:
        _suggest_groups(co, launches)
    elif "Most-launched" in sel:
        _top_apps(launches)
    elif "Recent sessions" in sel:
        _recent_sessions(launches)
    elif "Auto-create" in sel:
        _auto_create(co, launches)
    elif "Time-of-day" in sel:
        _time_analysis(launches)


# ─── Suggest patterns ─────────────────────────────────────────────────────────

def _suggest_groups(co: dict, launches: list):
    if not co:
        ui.notify("Smart Groups",
                  "Not enough history yet. Use your groups a few more times.")
        return

    sorted_pairs = sorted(co.items(), key=lambda x: x[1], reverse=True)[:20]
    lines = []
    for key, count in sorted_pairs:
        a, b = key.split("|||")
        lines.append(
            f"{Path(a).name:<22}+  {Path(b).name:<22}  opened together  {count}x"
        )

    if not lines:
        lines = ["No patterns yet — keep using your groups!"]

    ui.prompt("Co-occurrence Patterns", lines,
              message="Apps you frequently open together (higher = stronger pattern)")


# ─── Top apps ─────────────────────────────────────────────────────────────────

def _top_apps(launches: list):
    if not launches:
        ui.notify("Smart Groups", "No launch history yet.")
        return
    all_cmds = [Path(c).name for l in launches for c in l.get("commands", []) if c]
    counts   = Counter(all_cmds)
    lines    = [f"{name:<30}  {cnt:>4}x" for name, cnt in counts.most_common(20)]
    ui.prompt("Most-Launched Apps", lines, message=f"Based on {len(launches)} sessions")


# ─── Recent sessions ──────────────────────────────────────────────────────────

def _recent_sessions(launches: list):
    if not launches:
        ui.notify("Smart Groups", "No history yet.")
        return
    recent = launches[-10:][::-1]
    lines  = [
        f"{l['time'][:16].replace('T',' ')}   {l['group']:<20}"
        f"  ({len(l.get('commands',[]))} apps)"
        for l in recent
    ]
    ui.prompt("Recent Sessions", lines)


# ─── Auto-create ─────────────────────────────────────────────────────────────

def _auto_create(co: dict, launches: list):
    if len(co) < 3:
        ui.notify("Smart Groups",
                  "Need more history. Launch your groups several more times first.")
        return

    clusters = _build_clusters(co)
    if not clusters:
        ui.notify("Smart Groups", "Could not find strong clusters yet.")
        return

    # Show the top 3 cluster candidates
    choices = []
    for i, (cmds, strength) in enumerate(clusters[:3], 1):
        names = ", ".join(Path(c).name for c in cmds)
        choices.append(f"[{i}] {names}  (strength {strength:.0f})")
    choices.append("❌  Cancel")

    sel = ui.prompt("Pick a Cluster", choices,
                    message="Select a suggested cluster to create as a group")
    if not sel or "Cancel" in sel:
        return

    try:
        idx = int(sel[1]) - 1
    except (ValueError, IndexError):
        return

    cmds, _ = clusters[idx]
    names    = [Path(c).name for c in cmds]
    preview  = "\n".join(f"  • {n}" for n in names)

    confirm = ui.prompt(
        "Create Smart Group",
        ["✅  Yes, create it", "❌  Cancel"],
        message=f"Apps:\n{preview}",
    )
    if not confirm or "Cancel" in confirm:
        return

    name = ui.text_input("Group name", "Smart Group")
    if not name:
        return

    groups = config.load_groups()
    groups[name] = {
        "description": "Auto-generated from usage patterns",
        "color":       "#16A085",
        "apps": [
            {"name": n, "command": n, "delay": round(i * 0.6, 1)}
            for i, n in enumerate(names)
        ],
    }
    config.save_groups(groups)
    ui.notify("Smart Group Created",
              f'"{name}" with {len(names)} app(s).', icon="list-add")


def _build_clusters(co: dict, max_size: int = 6) -> list[tuple[list, float]]:
    """
    Greedy cluster building from co-occurrence matrix.
    Returns list of (commands_list, strength_score).
    """
    sorted_pairs = sorted(co.items(), key=lambda x: x[1], reverse=True)
    seen_seeds   = set()
    clusters     = []

    for seed_key, seed_count in sorted_pairs[:10]:
        a, b = seed_key.split("|||")
        seed = frozenset([a, b])
        if seed in seen_seeds:
            continue
        seen_seeds.add(seed)

        cluster  = set([a, b])
        strength = float(seed_count)

        for key, count in sorted_pairs:
            x, y = key.split("|||")
            if x in cluster or y in cluster:
                cluster.update([x, y])
                strength += count
            if len(cluster) >= max_size:
                break

        clusters.append((sorted(cluster), strength))

    # Sort by strength, deduplicate
    clusters.sort(key=lambda x: x[1], reverse=True)
    final, seen_sets = [], []
    for cmds, strength in clusters:
        s = frozenset(cmds)
        if s not in seen_sets:
            seen_sets.append(s)
            final.append((cmds, strength))

    return final[:5]


# ─── Time-of-day analysis ─────────────────────────────────────────────────────

def _time_analysis(launches: list):
    if not launches:
        ui.notify("Smart Groups", "No history yet.")
        return

    # Bucket by hour into Morning/Afternoon/Evening/Night
    buckets: dict[str, Counter] = {
        "🌅 Morning   (06–12)": Counter(),
        "☀️ Afternoon (12–18)": Counter(),
        "🌇 Evening   (18–23)": Counter(),
        "🌙 Night     (00–06)": Counter(),
    }

    def _bucket(hour: int) -> str:
        if   6  <= hour < 12: return "🌅 Morning   (06–12)"
        elif 12 <= hour < 18: return "☀️ Afternoon (12–18)"
        elif 18 <= hour < 23: return "🌇 Evening   (18–23)"
        else:                 return "🌙 Night     (00–06)"

    for l in launches:
        try:
            hour = datetime.fromisoformat(l["time"]).hour
        except Exception:
            continue
        bk = _bucket(hour)
        buckets[bk][l["group"]] += 1

    lines = []
    for period, counter in buckets.items():
        if not counter:
            continue
        lines.append(period)
        for grp, cnt in counter.most_common(3):
            lines.append(f"      {grp:<22}  {cnt}x")
        lines.append("─────────────────────────────────────────")

    if not lines:
        lines = ["Not enough data yet."]

    ui.prompt("Time-of-Day Usage", lines,
              message="Which groups you tend to open at different times of day")
