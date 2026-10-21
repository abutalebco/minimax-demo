"""Tic-Tac-Toe Minimax visualizer.  Run:  streamlit run app.py"""
import time

import pandas as pd
import streamlit as st

import engine as E

st.set_page_config(page_title="Tic-Tac-Toe Minimax Visualizer", page_icon="🎯", layout="wide")

ALGOS = {"Alpha-beta pruning": "alphabeta", "Minimax (plain)": "minimax"}
MARK = {"X": "❌", "O": "⭕"}
ICON = {1: "🟢", 0: "🟡", -1: "🔴"}
PRESETS = {  # '.' = empty cell
    "Open fight (5 empties)": "XO.XO....",
    "Win in one for X (3 empties)": "XOXOOX...",
    "Diagonal duel (5 empties)": "X.O.X...O",
    "O to move, win in one (4 empties)": "XX.OO.X..",
}
ss = st.session_state


# ------------------------------------------------------------------ helpers
def fmt(x):
    if x is None:
        return "-"
    return "inf" if x == E.INF else "-inf" if x == -E.INF else f"{x:+d}" if x else "0"


def parse(s):
    return tuple(" " if c == "." else c for c in s)


def sign_for(turn, v):
    """Value from the mover's perspective (+1 = forced win for the mover)."""
    return v if turn == "X" else -v


# ------------------------------------------------------------------ game logic
def place(i):
    ss.board[i] = ss.turn
    ss.log.append(f"{MARK[ss.turn]} cell {i + 1}")
    ss.turn = E.other(ss.turn)


def ai_move():
    b, me, algo = tuple(ss.board), ss.turn, ALGOS[ss.algo_label]
    t0 = time.perf_counter()
    res = E.search(b, me, algo)
    ms = (time.perf_counter() - t0) * 1000
    mm = res if algo == "minimax" else E.search(b, me, "minimax")
    ab = res if algo == "alphabeta" else E.search(b, me, "alphabeta")
    place(res.move)
    ss.last = dict(mark=me, cell=res.move + 1, value=sign_for(me, res.value), algo=ss.algo_label,
                   ms=ms, mm=mm.nodes, ab=ab.nodes)


def on_cell(i):
    b = tuple(ss.board)
    if E.is_terminal(b) or b[i] != " " or ss.turn != ss.human:
        return
    place(i)
    if not E.is_terminal(tuple(ss.board)):
        ai_move()


def new_game():
    ss.board, ss.turn, ss.log, ss.last = [" "] * 9, "X", [], None
    if ss.human == "O":
        ai_move()


def reset_step():
    ss.step = 0


ss.setdefault("human", "X")
ss.setdefault("algo_label", "Alpha-beta pruning")
ss.setdefault("hints", True)
ss.setdefault("step", 0)
if "board" not in ss:
    new_game()

# ------------------------------------------------------------------ styling + sidebar
st.markdown("""<style>
[class*="st-key-cell_"] button {height: 4.6rem; font-size: 1.6rem;}
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Settings")
    st.radio("You play as", ["X", "O"], key="human", on_change=new_game,
             format_func=lambda m: f"{MARK[m]} {m} ({'moves first' if m == 'X' else 'moves second'})")
    st.radio("AI algorithm", list(ALGOS), key="algo_label")
    st.checkbox("Show move values (hints)", key="hints")
    st.button("New game", on_click=new_game, use_container_width=True)
    st.caption("X is MAX, O is MIN. Values: +1 forced win, 0 draw, -1 forced loss "
               "(from the mover's point of view, assuming perfect play).")

st.title("🎯 Tic-Tac-Toe: Minimax Visualizer")
tab_play, tab_tree = st.tabs(["🎮 Play vs AI", "🌳 Step-by-step tree explorer"])

# ------------------------------------------------------------------ PLAY TAB
with tab_play:
    left, right = st.columns([1, 1.2], gap="large")
    b = tuple(ss.board)
    over = E.is_terminal(b)
    my_turn = (not over) and ss.turn == ss.human

    with left:
        vals = E.move_values(b, ss.turn) if (my_turn and ss.hints) else {}
        for r in range(3):
            cols = st.columns(3)
            for c in range(3):
                i = 3 * r + c
                if b[i] != " ":
                    label, disabled = MARK[b[i]], True
                else:
                    disabled = not my_turn
                    if i in vals:
                        pv = sign_for(ss.turn, vals[i])
                        label = f"{ICON[pv]} {fmt(pv)}"
                    else:
                        label = "·"
                cols[c].button(label, key=f"cell_{i}", disabled=disabled, on_click=on_cell,
                               args=(i,), use_container_width=True)
        w = E.winner(b)
        if w:
            (st.success if w == ss.human else st.error)(
                "You win! 🎉" if w == ss.human else f"The AI ({MARK[w]}) wins.")
        elif over:
            st.info("Draw. 🤝 (Perfect play always draws tic-tac-toe.)")
        else:
            st.write(f"**Your turn** ({MARK[ss.turn]})" + ("  \nHints show what each move is worth." if ss.hints else ""))
        if ss.log:
            st.caption("Moves: " + "  →  ".join(ss.log))

    with right:
        st.subheader("What the AI just did")
        L = ss.last
        if not L:
            st.write("Make a move. The AI will search the game tree and reply, "
                     "then show how much work minimax vs alpha-beta needed.")
        else:
            verdict = {1: "forced win", 0: "draw", -1: "forced loss"}[L["value"]]
            st.write(f"{MARK[L['mark']]} played **cell {L['cell']}** using *{L['algo']}* in "
                     f"{L['ms']:.1f} ms. Best outcome it can force: **{verdict}**.")
            m1, m2, m3 = st.columns(3)
            m1.metric("Minimax nodes", f"{L['mm']:,}")
            m2.metric("Alpha-beta nodes", f"{L['ab']:,}")
            m3.metric("Nodes skipped", f"{100 * (1 - L['ab'] / L['mm']):.0f}%")
            st.bar_chart(pd.DataFrame({"nodes searched": [L["mm"], L["ab"]]},
                                      index=["Minimax", "Alpha-beta"]), horizontal=True)
            st.caption("Both algorithms choose a move of the same value; "
                       "alpha-beta just skips branches that cannot change the answer.")

# ------------------------------------------------------------------ TREE TAB
@st.cache_data(show_spinner=False)
def get_trace(board, turn, algo):
    try:
        return E.trace_search(board, turn, algo)
    except E.TraceTooLarge:
        return None


def describe(e):
    t = e["type"]
    who = lambda tn: "MAX (X)" if tn == "X" else "MIN (O)"
    if t == "enter":
        where = "Start at the root" if e["parent"] is None else f"Go down by playing cell {e['move'] + 1}"
        ab = f" Window: alpha={fmt(e['alpha'])}, beta={fmt(e['beta'])}." if e["alpha"] is not None else ""
        return f"{where}. {who(e['turn'])} to move.{ab}"
    if t == "leaf":
        return f"Game over here, so utility = **{fmt(e['value'])}**."
    if t == "exit":
        pick = "largest" if e["turn"] == "X" else "smallest"
        return f"All children done. {who(e['turn'])} takes the {pick} child value: **{fmt(e['value'])}**. Back up."
    cells = ", ".join(str(m + 1) for m in e["moves"])
    return (f"✂️ **Cut-off!** alpha ({fmt(e['alpha'])}) ≥ beta ({fmt(e['beta'])}). "
            f"Skipping cell(s) {cells}: they cannot change the result.")


def render_dot(events):
    nodes, cur = {}, None
    for e in events:
        n = e["id"]
        if e["type"] == "enter":
            nodes[n] = dict(e, value=None, state="open", stubs=())
        elif e["type"] == "leaf":
            nodes[n].update(value=e["value"], state="leaf")
        elif e["type"] == "exit":
            nodes[n].update(value=e["value"], state="done")
        else:
            nodes[n]["stubs"] = e["moves"]
        cur = n
    compact = len(nodes) > 90
    out = ['digraph G {', 'rankdir=TB;',
           'node [shape=box, style="filled,rounded", fontname="Courier", fontsize=%d];' % (8 if compact else 10),
           'edge [fontsize=9, color="#718096"];']
    for n, d in nodes.items():
        maxi = d["turn"] == "X"
        val = "…" if d["value"] is None else fmt(d["value"])
        if compact:
            label = val
        else:
            rows = "\\n".join("".join(c if c != " " else "·" for c in d["board"][r:r + 3]) for r in (0, 3, 6))
            head = "MAX" if maxi else "MIN"
            ab = f"\\na={fmt(d['alpha'])} b={fmt(d['beta'])}" if d["alpha"] is not None else ""
            label = f"{head}\\n{rows}\\nv={val}{ab}"
        fill = ("#faf089" if n == cur else "#c6f6d5" if d["state"] == "leaf"
                else ("#bee3f8" if maxi else "#fed7d7") if d["state"] == "done" else "white")
        color = "#2b6cb0" if maxi else "#c53030"
        out.append(f'n{n} [label="{label}", fillcolor="{fill}", color="{color}", penwidth={3 if n == cur else 1.5}];')
        if d["parent"] is not None:
            out.append(f'n{d["parent"]} -> n{n} [label="{d["move"] + 1}"];')
        for m in d["stubs"]:
            out.append(f's{n}_{m} [label="✂", fillcolor="#e2e8f0", color="#a0aec0", style="filled,dashed", fontcolor="#718096"];')
            out.append(f'n{n} -> s{n}_{m} [label="{m + 1}", style=dashed, color="#a0aec0"];')
    out.append("}")
    return "\n".join(out)


def jump(delta=None, to=None):
    ss.step = to if to is not None else ss.step + delta


with tab_tree:
    st.write("Watch the search happen one step at a time. Cells are numbered 1-9 (left to right, top to bottom); "
             "edge labels show the move played. **Yellow** = current node, **green** = game over, "
             "**blue/red** = finished MAX/MIN node, **✂** = branch skipped by alpha-beta.")
    c1, c2 = st.columns([1.3, 1])
    cur_board = tuple(ss.board)
    pos = c1.selectbox("Position to analyse", ["Current game board"] + list(PRESETS), on_change=reset_step, key="pos")
    algo_t = ALGOS[c2.radio("Algorithm", list(ALGOS), horizontal=True, key="algo_tree", on_change=reset_step)]
    board = cur_board if pos == "Current game board" else parse(PRESETS[pos])
    turn = E.turn_of(board)

    st.code("\n".join(" ".join(c if c != " " else "." for c in board[r:r + 3]) for r in (0, 3, 6))
            + f"\n\n{turn} to move", language=None)

    if E.is_terminal(board):
        st.info("This position is already finished. Pick another one.")
    else:
        events = get_trace(board, turn, algo_t)
        mm_n, ab_n = E.search(board, turn, "minimax").nodes, E.search(board, turn, "alphabeta").nodes
        if events is None:
            st.warning(f"The full search tree is too big to draw ({mm_n:,} nodes for minimax, {ab_n:,} for alpha-beta). "
                       "Choose a preset, or play a few more moves so fewer cells are empty "
                       "(alpha-beta handles more empties than plain minimax).")
        else:
            n = len(events)
            ss.step = max(0, min(ss.step, n))
            b1, b2, b3, b4, b5, b6 = st.columns(6)
            b1.button("⏮ Start", on_click=jump, kwargs=dict(to=0), use_container_width=True)
            b2.button("−10", on_click=jump, kwargs=dict(delta=-10), use_container_width=True)
            b3.button("◀ Back", on_click=jump, kwargs=dict(delta=-1), use_container_width=True)
            b4.button("Next ▶", on_click=jump, kwargs=dict(delta=1), use_container_width=True)
            b5.button("+10", on_click=jump, kwargs=dict(delta=10), use_container_width=True)
            b6.button("End ⏭", on_click=jump, kwargs=dict(to=n), use_container_width=True)
            ss.step = max(0, min(ss.step, n))
            st.slider("Step", 0, n, key="step")
            if ss.step == 0:
                st.write("Press **Next ▶** to start the search.")
            else:
                st.write(f"**Step {ss.step}/{n}:** " + describe(events[ss.step - 1]))
                st.graphviz_chart(render_dot(events[:ss.step]), use_container_width=True)
            if ss.step == n and n:
                root = events[-1]["value"]
                st.success(f"Root value = {fmt(root)}: with perfect play this position is a "
                           f"{'win for X' if root == 1 else 'win for O' if root == -1 else 'draw'}.")
            m1, m2, m3 = st.columns(3)
            m1.metric("Minimax nodes (full search)", f"{mm_n:,}")
            m2.metric("Alpha-beta nodes", f"{ab_n:,}")
            m3.metric("Saved by pruning", f"{100 * (1 - ab_n / mm_n):.0f}%")
