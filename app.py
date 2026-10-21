"""Tic-Tac-Toe Minimax & Alpha-Beta Live Tree Visualizer.  Run:  streamlit run app.py"""
import time

import pandas as pd
import streamlit as st

import engine as E

st.set_page_config(
    page_title="Minimax live tree",
    page_icon=":material/account_tree:",
    layout="wide",
)

ALGOS = {"Alpha-beta": "alphabeta", "Minimax": "minimax"}
MARK = {"X": "❌", "O": "⭕"}
ICON = {1: "🟢", 0: "🟡", -1: "🔴"}
PRESETS = {
    "Open fight (5 empties)": "XO.XO....",
    "Diagonal duel (5 empties)": "X.O.X...O",
    "O to move, win in 1 (4 empties)": "XX.OO.X..",
    "X to move, win in 1 (3 empties)": "XOXOOX...",
    "Empty board (9 empties)": ".........",
}
DEPTH_OPTS = ["Auto", "1 ply", "2 plies", "3 plies", "Full"]
ss = st.session_state


def fmt(x):
    if x is None:
        return "-"
    return "∞" if x == E.INF else "-∞" if x == -E.INF else f"{x:+d}" if x else "0"


def parse(s):
    return tuple(" " if c == "." else c for c in s)


def sign_for(turn, v):
    return v if turn == "X" else -v


@st.cache_data(max_entries=256, show_spinner=False)
def get_live_trace(board: tuple, turn: str, algo: str, depth_choice: str):
    empties = board.count(" ")
    if depth_choice == "Full":
        candidates = [None, 5, 4, 3, 2, 1]
        cap = 320
    elif depth_choice == "Auto":
        candidates = [None, 4, 3, 2, 1]
        cap = 140
    else:
        d0 = int(depth_choice.split()[0])
        candidates = [d0, max(1, d0 - 1), 1]
        cap = 320
    for d in candidates:
        try:
            return E.trace_search(board, turn, algo, cap=cap, max_depth=d), d or empties
        except E.TraceTooLarge:
            continue
    return E.trace_search(board, turn, algo, cap=320, max_depth=1), 1


@st.cache_data(max_entries=256, show_spinner=False)
def compare_algos(board: tuple, turn: str):
    return E.search(board, turn, "minimax"), E.search(board, turn, "alphabeta")


def set_trace_target(board: tuple, turn: str, chosen_move: int | None = None, autoplay: bool = True):
    ss.trace_board = board
    ss.trace_turn = turn
    ss.trace_move = chosen_move
    ss.step = 1
    ss.playing = autoplay and not E.is_terminal(board)


def place(i: int):
    ss.history.append((list(ss.board), ss.turn, ss.last, ss.trace_board, ss.trace_turn, ss.trace_move))
    ss.board[i] = ss.turn
    ss.log.append(f"{ss.turn}→{i + 1}")
    ss.turn = E.other(ss.turn)


def run_ai_turn():
    b = tuple(ss.board)
    if E.is_terminal(b):
        return
    me = ss.turn
    algo = ALGOS[ss.algo_label]
    t0 = time.perf_counter()
    res = E.search(b, me, algo)
    ms = (time.perf_counter() - t0) * 1000
    mm, ab = compare_algos(b, me)
    set_trace_target(b, me, chosen_move=res.move, autoplay=ss.auto_animate)
    place(res.move)
    ss.last = dict(
        mark=me,
        cell=res.move + 1,
        move=res.move,
        value=sign_for(me, res.value),
        algo=ss.algo_label,
        ms=ms,
        mm=mm.nodes,
        ab=ab.nodes,
    )


def on_cell(i: int):
    b = tuple(ss.board)
    if E.is_terminal(b) or b[i] != " ":
        return
    place(i)
    nxt = tuple(ss.board)
    if not E.is_terminal(nxt):
        if ss.vs_ai:
            run_ai_turn()
        else:
            set_trace_target(nxt, ss.turn, autoplay=ss.auto_animate)
    else:
        set_trace_target(b, E.other(ss.turn), chosen_move=i, autoplay=False)


def load_board(b: tuple):
    ss.board = list(b)
    ss.turn = E.turn_of(b)
    ss.log = []
    ss.history = []
    ss.last = None
    if ss.vs_ai and ss.turn != ss.human and not E.is_terminal(b):
        run_ai_turn()
    else:
        set_trace_target(b, ss.turn, autoplay=ss.auto_animate)


def new_game():
    load_board(parse(PRESETS[ss.preset_sel]))


def undo_move():
    if not ss.history:
        return
    steps = 2 if (ss.vs_ai and len(ss.history) >= 2) else 1
    for _ in range(steps):
        if ss.history:
            b, t, last, tb, tt, tm = ss.history.pop()
            if ss.log:
                ss.log.pop()
    ss.board, ss.turn, ss.last = b, t, last
    ss.trace_board, ss.trace_turn, ss.trace_move = tb, tt, tm
    ss.step = 1
    ss.playing = False


def sync_trace_settings():
    ss.step = 1
    ss.playing = ss.auto_animate and not E.is_terminal(ss.trace_board)


ss.setdefault("human", "X")
ss.setdefault("vs_ai", True)
ss.setdefault("algo_label", "Alpha-beta")
ss.setdefault("depth_choice", "Auto")
ss.setdefault("speed", 6)
ss.setdefault("auto_animate", True)
ss.setdefault("hints", True)
ss.setdefault("preset_sel", "Open fight (5 empties)")
if "board" not in ss:
    new_game()


def describe_event(e: dict) -> str:
    t = e["type"]
    if t == "leaf":
        kind = "Horizon eval" if e.get("cutoff") else "Terminal leaf"
        return f":material/flag: {kind} → utility **{fmt(e['value'])}**"
    who = "MAX (X)" if e["turn"] == "X" else "MIN (O)"
    if t == "enter":
        where = "Root position" if e["parent"] is None else f"Expand cell **{e['move'] + 1}** (ply {e['depth']})"
        ab = f" · window `[α={fmt(e['alpha'])}, β={fmt(e['beta'])}]`" if e["alpha"] is not None else ""
        return f":material/account_tree: {where} — **{who}** to move{ab}"
    if t == "exit":
        pick = "max" if e["turn"] == "X" else "min"
        return f":material/upgrade: Backtrack **{who}** ({pick} child) → value **{fmt(e['value'])}**"
    cells = ", ".join(str(m + 1) for m in e["moves"])
    return f":material/content_cut: **Alpha-beta cutoff!** `α ({fmt(e['alpha'])}) ≥ β ({fmt(e['beta'])})` — pruned cell(s) **{cells}**"


def render_tree_svg(events: list, chosen_move: int | None) -> str:
    """Fast, zero-flicker SVG renderer for the live search tree."""
    nodes, children, cur = {}, {}, None
    for e in events:
        n = e["id"]
        if e["type"] == "enter":
            nodes[n] = dict(e, value=None, state="open", stubs=(), cutoff=False)
            children.setdefault(n, [])
            if e["parent"] is not None:
                children.setdefault(e["parent"], []).append(n)
        elif e["type"] == "leaf":
            nodes[n].update(value=e["value"], state="leaf", cutoff=e.get("cutoff", False))
        elif e["type"] == "exit":
            nodes[n].update(value=e["value"], state="done")
        else:
            nodes[n]["stubs"] = e["moves"]
        cur = n

    # Attach pruned stub pseudo-nodes so they lay out cleanly
    for n, d in list(nodes.items()):
        for m in d["stubs"]:
            sid = f"s_{n}_{m}"
            nodes[sid] = dict(
                id=sid,
                parent=n,
                move=m,
                depth=d["depth"] + 1,
                state="pruned",
                turn="X" if d["turn"] == "O" else "O",
                value=None,
                board=None,
            )
            children.setdefault(n, []).append(sid)
            children.setdefault(sid, [])

    total_nodes = len(nodes)
    compact = total_nodes > 28
    nw = 44 if compact else 72
    nh = 34 if compact else 76
    x_gap = 10 if compact else 16
    y_gap = 54 if compact else 98

    pos_x = {}
    leaf_cursor = [0]

    def layout(u):
        ch = children.get(u, [])
        if not ch:
            pos_x[u] = leaf_cursor[0] * (nw + x_gap)
            leaf_cursor[0] += 1
            return pos_x[u]
        xs = [layout(c) for c in ch]
        pos_x[u] = 0.5 * (xs[0] + xs[-1])
        return pos_x[u]

    layout(0)
    max_depth = max((d["depth"] for d in nodes.values()), default=0)
    width = max(560, int(max(pos_x.values(), default=0) + nw + 40))
    height = max(220, int((max_depth + 1) * y_gap + nh + 24))
    x_offset = max(20.0, (width - (max(pos_x.values(), default=0) + nw)) / 2.0)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'style="font-family:Inter,system-ui,sans-serif;">'
    ]
    # Edges
    for n, d in nodes.items():
        p = d["parent"]
        if p is None:
            continue
        x1 = pos_x[p] + x_offset + nw / 2
        y1 = nodes[p]["depth"] * y_gap + 14 + nh
        x2 = pos_x[n] + x_offset + nw / 2
        y2 = d["depth"] * y_gap + 14
        is_pruned = d["state"] == "pruned"
        is_best = p == 0 and chosen_move is not None and d["move"] == chosen_move and not is_pruned
        stroke = "#94A3B8" if is_pruned else "#16A34A" if is_best else "#64748B"
        sw = 2.6 if is_best else 1.4
        dash = ' stroke-dasharray="4,3"' if is_pruned else ""
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{dash}/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        elbl = f"★{d['move'] + 1}" if is_best else f"c{d['move'] + 1}"
        svg.append(
            f'<rect x="{mx - 13:.1f}" y="{my - 8:.1f}" width="26" height="15" rx="4" fill="#0F172A" opacity="0.82"/>'
            f'<text x="{mx:.1f}" y="{my + 3:.1f}" text-anchor="middle" font-size="9.5" font-weight="600" fill="#F8FAFC">{elbl}</text>'
        )

    # Nodes
    for n, d in nodes.items():
        x = pos_x[n] + x_offset
        y = d["depth"] * y_gap + 14
        st_name = d["state"]
        if st_name == "pruned":
            svg.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{nw}" height="{nh}" rx="6" '
                f'fill="#F1F5F9" stroke="#94A3B8" stroke-width="1.3" stroke-dasharray="4,3"/>'
                f'<text x="{x + nw / 2:.1f}" y="{y + nh / 2 + 4:.1f}" text-anchor="middle" '
                f'font-size="11" font-weight="600" fill="#64748B">✂ c{d["move"] + 1}</text>'
            )
            continue

        maxi = d["turn"] == "X"
        is_cur = n == cur
        is_best = d["parent"] == 0 and chosen_move is not None and d["move"] == chosen_move
        fill = (
            "#FEF08A" if is_cur
            else "#DCFCE7" if st_name == "leaf"
            else ("#DBEAFE" if maxi else "#FEE2E2") if st_name == "done"
            else "#F8FAFC"
        )
        stroke = "#CA8A04" if is_cur else "#16A34A" if is_best else ("#2563EB" if maxi else "#DC2626")
        sw = 2.8 if (is_cur or is_best) else 1.5
        val = "…" if d["value"] is None else fmt(d["value"])
        svg.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{nw}" height="{nh}" rx="7" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
        )
        if compact:
            role = "X" if maxi else "O"
            svg.append(
                f'<text x="{x + nw / 2:.1f}" y="{y + 13:.1f}" text-anchor="middle" font-size="9" font-weight="700" fill="#334155">{role}</text>'
                f'<text x="{x + nw / 2:.1f}" y="{y + 27:.1f}" text-anchor="middle" font-size="11" font-weight="700" fill="#0F172A">{val}</text>'
            )
        else:
            role = "MAX (X)" if maxi else "MIN (O)"
            svg.append(
                f'<text x="{x + nw / 2:.1f}" y="{y + 12:.1f}" text-anchor="middle" font-size="9" font-weight="700" fill="{stroke}">{role}</text>'
            )
            # Mini 3x3 board inside the node
            gx, gy, cs = x + 18, y + 16, 12
            b_cells = d["board"]
            for r in range(3):
                for c in range(3):
                    cx, cy = gx + c * cs, gy + r * cs
                    mark = b_cells[3 * r + c]
                    mcol = "#1D4ED8" if mark == "X" else "#DC2626" if mark == "O" else "#94A3B8"
                    ch_txt = mark if mark != " " else "·"
                    svg.append(
                        f'<text x="{cx + 6:.1f}" y="{cy + 9:.1f}" text-anchor="middle" '
                        f'font-family="JetBrains Mono,monospace" font-size="9.5" font-weight="700" fill="{mcol}">{ch_txt}</text>'
                    )
            ab_txt = f" [{fmt(d['alpha'])},{fmt(d['beta'])}]" if d.get("alpha") is not None else ""
            svg.append(
                f'<text x="{x + nw / 2:.1f}" y="{y + 68:.1f}" text-anchor="middle" font-size="9.5" font-weight="700" fill="#0F172A">v={val}{ab_txt}</text>'
            )
    svg.append("</svg>")
    return "".join(svg)


# ------------------------------------------------------------------ SIDEBAR
with st.sidebar:
    st.subheader(":material/tune: Live search controls")
    st.selectbox("Scenario / preset", list(PRESETS), key="preset_sel", on_change=new_game)
    st.segmented_control(
        "Algorithm",
        list(ALGOS),
        key="algo_label",
        on_change=sync_trace_settings,
        width="stretch",
    )
    st.segmented_control(
        "Tree depth",
        DEPTH_OPTS,
        key="depth_choice",
        on_change=sync_trace_settings,
        width="stretch",
    )
    st.slider("Playback speed (events / tick)", 1, 25, key="speed")
    st.toggle("Auto-animate tree on move", key="auto_animate")
    st.toggle("Show exact move hints", key="hints")
    st.toggle("Auto-reply with AI", key="vs_ai")
    st.segmented_control(
        "You play as",
        ["X", "O"],
        key="human",
        on_change=new_game,
        format_func=lambda m: f"{MARK[m]} {m}",
        width="stretch",
    )
    st.caption(
        "X is **MAX** (+1 win), O is **MIN** (-1 win). "
        "Play on the board or click root branches in the tree."
    )

# ------------------------------------------------------------------ HEADER
st.title(":material/account_tree: Tic-tac-toe minimax live action")

left_col, right_col = st.columns([1, 1.9], gap="large")

# ------------------------------------------------------------------ LEFT: BOARD & METRICS
with left_col:
    b = tuple(ss.board)
    over = E.is_terminal(b)
    w = E.winner(b)

    with st.container(border=True):
        top_row = st.container(horizontal=True, vertical_alignment="center")
        with top_row:
            st.subheader(":material/grid_on: Game board")
            if w:
                st.badge(f"{w} wins!", icon=":material/emoji_events:", color="green" if w == ss.human else "red")
            elif over:
                st.badge("Draw game", icon=":material/handshake:", color="blue")
            else:
                st.badge(f"{ss.turn} to move", icon=":material/play_arrow:", color="violet")

        vals = E.move_values(b, ss.turn) if (not over and ss.hints) else {}
        last_ai_cell = ss.last["move"] if ss.last else None

        for r in range(3):
            cols = st.columns(3, gap="small")
            for c in range(3):
                i = 3 * r + c
                if b[i] != " ":
                    label, disabled = f"{MARK[b[i]]}", True
                else:
                    disabled = over
                    if i in vals:
                        pv = sign_for(ss.turn, vals[i])
                        label = f"{ICON[pv]} {fmt(pv)}"
                    else:
                        label = f"· {i + 1} ·"
                btn_type = "primary" if i == last_ai_cell else "secondary"
                cols[c].button(
                    label,
                    key=f"cell_{i}",
                    disabled=disabled,
                    type=btn_type,
                    on_click=on_cell,
                    args=(i,),
                    width="stretch",
                )

        act_row = st.container(horizontal=True)
        act_row.button(":material/restart_alt: Reset", on_click=new_game, width="stretch")
        act_row.button(":material/undo: Undo", on_click=undo_move, disabled=not ss.history, width="stretch")
        act_row.button(":material/smart_toy: AI move", on_click=run_ai_turn, disabled=over, width="stretch")

        if not over and st.button(":material/visibility: Search current board in tree", width="stretch"):
            set_trace_target(b, ss.turn, autoplay=ss.auto_animate)

        if ss.log:
            st.caption("Moves: " + " → ".join(ss.log))

    with st.container(border=True):
        st.subheader(":material/speed: Search efficiency")
        tb, tt = ss.trace_board, ss.trace_turn
        if not E.is_terminal(tb):
            mm_res, ab_res = compare_algos(tb, tt)
            saved = 100 * (1 - ab_res.nodes / max(1, mm_res.nodes))
            m1, m2, m3 = st.columns(3)
            m1.metric("Minimax", f"{mm_res.nodes:,}", border=True)
            m2.metric("Alpha-beta", f"{ab_res.nodes:,}", border=True)
            m3.metric("Pruned", f"{saved:.0f}%", border=True)
            chart_df = pd.DataFrame(
                {"Nodes": [mm_res.nodes, ab_res.nodes]},
                index=["Minimax", "Alpha-beta"],
            )
            st.bar_chart(
                chart_df,
                horizontal=True,
                height=120,
                alt="Horizontal bar chart comparing nodes searched by Minimax and Alpha-beta pruning",
            )


# ------------------------------------------------------------------ RIGHT: LIVE GAME TREE FRAGMENT
@st.fragment(run_every=0.35 if ss.get("playing", False) else None)
def live_tree_panel():
    tb = ss.trace_board
    tt = ss.trace_turn
    algo = ALGOS[ss.algo_label]

    with st.container(border=True):
        if E.is_terminal(tb):
            st.info(
                "This board position is already terminal. Reset or pick a preset to watch the search tree.",
                title="Game over",
            )
            return

        events, used_depth = get_live_trace(tb, tt, algo, ss.depth_choice)
        total = len(events)
        ss.step = max(1, min(ss.step, total))

        hdr = st.container(horizontal=True, vertical_alignment="center")
        with hdr:
            st.subheader(f":material/account_tree: Live game tree ({ss.algo_label})")
            st.badge(f"{tt} searching", color="blue" if tt == "X" else "red")
            st.badge(f"Depth ≤ {used_depth}", color="gray")
            if ss.trace_move is not None:
                st.badge(f"AI chose cell {ss.trace_move + 1}", icon=":material/star:", color="green")

        # Interactive root branch buttons (play directly from the tree!)
        cur_board = tuple(ss.board)
        if not E.is_terminal(cur_board):
            root_vals = E.move_values(cur_board, ss.turn)
            branch_row = st.container(horizontal=True, vertical_alignment="center")
            branch_row.caption("Play root branch:")
            for m in E.legal_moves(cur_board):
                pv = sign_for(ss.turn, root_vals[m])
                branch_row.button(
                    f"c{m + 1} ({fmt(pv)})",
                    key=f"tree_branch_{m}",
                    on_click=on_cell,
                    args=(m,),
                )

        # Playback controls
        ctrl = st.container(horizontal=True, vertical_alignment="center")
        play_lbl = ":material/pause: Pause" if ss.playing else ":material/play_arrow: Play live"
        if ctrl.button(play_lbl, type="primary", width="stretch"):
            if not ss.playing and ss.step >= total:
                ss.step = 1
            ss.playing = not ss.playing
            st.rerun()
        if ctrl.button(":material/first_page: Start", width="stretch"):
            ss.step = 1
            ss.playing = False
            st.rerun()
        if ctrl.button(":material/chevron_left: -1", width="stretch"):
            ss.step = max(1, ss.step - 1)
            ss.playing = False
        if ctrl.button(":material/chevron_right: +1", width="stretch"):
            ss.step = min(total, ss.step + 1)
            ss.playing = False
        if ctrl.button(":material/last_page: Full tree", width="stretch"):
            ss.step = total
            ss.playing = False
            st.rerun()

        step_val = st.slider(
            "Search timeline",
            min_value=1,
            max_value=total,
            value=ss.step,
            label_visibility="collapsed",
        )
        if step_val != ss.step:
            ss.step = step_val
            ss.playing = False

        cur_slice = events[: ss.step]
        active_ev = cur_slice[-1]
        visited_cnt = sum(1 for e in cur_slice if e["type"] == "enter")
        pruned_cnt = sum(len(e["moves"]) for e in cur_slice if e["type"] == "prune")
        leaves_cnt = sum(1 for e in cur_slice if e["type"] == "leaf")

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Step", f"{ss.step}/{total}", border=True)
        s2.metric("Nodes opened", f"{visited_cnt}", border=True)
        s3.metric("Leaves scored", f"{leaves_cnt}", border=True)
        s4.metric("Pruned ✂", f"{pruned_cnt}", border=True)

        st.markdown(describe_event(active_ev))
        st.image(render_tree_svg(cur_slice, ss.trace_move), width="stretch", alt="Live minimax and alpha-beta game tree")
        st.caption(
            "🟡 Active node · 🟢 Leaf / ★ Best move · 🔵 MAX done · 🔴 MIN done · ✂ Alpha-beta pruned branch"
        )

        if ss.playing:
            if ss.step < total:
                ss.step = min(total, ss.step + ss.speed)
            else:
                ss.playing = False
                st.rerun()


with right_col:
    live_tree_panel()
