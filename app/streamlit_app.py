"""Chat UI: answer + generated SQL + result table + automatic chart.  Run: streamlit run app/streamlit_app.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from i18n import LANGUAGES, STRINGS  # noqa: E402
from sqlagent.features import PRESETS  # noqa: E402
from sqlagent.graph import build_graph  # noqa: E402
from sqlagent.viz import choose_chart  # noqa: E402

DBS = {"db_small": "data/northwind_small.db", "db_full": "data/northwind_full.db"}

st.set_page_config(page_title="SQL Agent", page_icon=":material/database:", layout="wide")


@st.cache_resource
def get_graph(preset: str, db_path: str):
    return build_graph(PRESETS[preset], with_answer=True, db_path=db_path)


# Language is a UI-only setting: the agent answers in the language of the question on its own.
st.session_state.setdefault("lang", "tr")
st.session_state.setdefault("messages", [])


def t(key: str, **kw):
    text = STRINGS[st.session_state.lang][key]
    return text.format(**kw) if kw else text


def render_chart(df: pd.DataFrame, spec) -> None:
    if spec.kind == "none":
        if spec.reason and len(df) >= 2:  # single-row results need no explanation
            st.caption(t(f"chart_{spec.reason}"))
        return
    plot = px.line if spec.kind == "line" else px.bar
    kwargs = {"markers": True} if spec.kind == "line" else {"barmode": "group"}
    df = df.copy()
    df[spec.x] = df[spec.x].astype(str)
    fig = plot(df, x=spec.x, y=list(spec.ys), **kwargs)
    single = len(spec.ys) == 1
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), legend_title_text="", showlegend=not single,
                      yaxis_title=spec.ys[0] if single else None)
    st.plotly_chart(fig, use_container_width=True)


def render_assistant(m: dict) -> None:
    if m.get("error"):
        st.error(t("error", err=m["error"]))
        return
    if m.get("blocked"):
        st.warning(m["content"])
    elif m.get("abstain"):
        st.info(m["content"])
    else:
        st.markdown(m["content"] or t("no_result"))
    if m.get("sql"):
        with st.expander(t("used_sql")):
            st.code(m["sql"], language="sql")
    if m.get("df") is not None and not m["df"].empty:
        st.dataframe(m["df"], use_container_width=True, hide_index=True)
        render_chart(m["df"], choose_chart(list(m["df"].columns), [tuple(r) for r in m["df"].itertuples(index=False)]))
    if m.get("stats"):
        st.caption(t("meta", **m["stats"]))  # formatted at render time so it follows the UI language


with st.sidebar:
    lang_label = st.radio(t("language"), list(LANGUAGES), horizontal=True,
                          index=list(LANGUAGES.values()).index(st.session_state.lang))
    if LANGUAGES[lang_label] != st.session_state.lang:
        st.session_state.lang = LANGUAGES[lang_label]
        st.rerun()
    st.title(t("title"))
    db_key = st.selectbox(t("database"), list(DBS), format_func=t)
    preset = st.selectbox(t("config"), list(PRESETS), index=list(PRESETS).index("full"), help=t("config_help"))
    st.caption(t("safety"))
    if st.button(t("clear")):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.caption(t("examples_title"))
    for ex in STRINGS[st.session_state.lang]["examples"]:
        if st.button(ex, use_container_width=True):
            st.session_state.pending = ex

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m["role"] == "assistant":
            render_assistant(m)
        else:
            st.markdown(m["content"])

question = st.chat_input(t("chat_input")) or st.session_state.pop("pending", None)
if question:
    history = [{"q": m["standalone"], "sql": m["sql"]} for m in st.session_state.messages
              if m["role"] == "assistant" and m.get("sql")]
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner(t("spinner")):
            try:
                out = get_graph(preset, DBS[db_key]).invoke({"question": question, "history": history})
                cols, rows = out.get("columns", []), out.get("rows", [])
                msg = {
                    "role": "assistant", "content": out.get("answer", ""),
                    "sql": out.get("sql", "") if not out.get("abstain") else "", "standalone": out["standalone"],
                    "abstain": out.get("abstain", ""), "blocked": out.get("blocked", False) and bool(out.get("error")),
                    "df": pd.DataFrame(rows, columns=cols) if rows and not out.get("error") else None,
                    "stats": {"attempts": out["attempts"], "tokens": out["tokens"], "rows": len(rows)},
                }
            except Exception as e:  # keep the chat alive on API/network failures
                msg = {"role": "assistant", "content": "", "error": str(e), "sql": "", "standalone": question}
        render_assistant(msg)
    st.session_state.messages.append(msg)
