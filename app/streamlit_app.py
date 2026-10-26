"""Chat UI: answer + generated SQL + result table + automatic chart.  Run: streamlit run app/streamlit_app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from sqlagent.features import PRESETS  # noqa: E402
from sqlagent.graph import build_graph  # noqa: E402
from sqlagent.viz import choose_chart  # noqa: E402

DBS = {"Northwind (küçük örnek)": "data/northwind_small.db", "Northwind (tam)": "data/northwind_full.db"}
EXAMPLES = [
    "En çok sipariş veren 5 müşteri kim?",
    "Total revenue per product category",
    "1996 yılında aylık sipariş sayısı",
    "Which employees never handled an order shipped to Spain?",
]

st.set_page_config(page_title="SQL Ajanı", page_icon=":material/database:", layout="wide")


@st.cache_resource
def get_graph(preset: str, db_path: str):
    return build_graph(PRESETS[preset], with_answer=True, db_path=db_path)


def render_chart(df: pd.DataFrame, spec) -> None:
    if spec.kind == "none":
        if spec.reason and len(df) >= 2:  # single-row results need no explanation
            st.caption(spec.reason)
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
    kind = m.get("abstain")
    if m.get("blocked"):
        st.warning(m["content"])
    elif kind == "clarify":
        st.info(m["content"])
    elif kind == "cannot_answer":
        st.info(m["content"])
    else:
        st.markdown(m["content"])
    if m.get("sql"):
        with st.expander("Kullanılan SQL"):
            st.code(m["sql"], language="sql")
    if m.get("df") is not None and not m["df"].empty:
        st.dataframe(m["df"], use_container_width=True, hide_index=True)
        render_chart(m["df"], choose_chart(list(m["df"].columns), [tuple(r) for r in m["df"].itertuples(index=False)]))
    if m.get("meta"):
        st.caption(m["meta"])


with st.sidebar:
    st.title("SQL Ajanı")
    db_label = st.selectbox("Veritabanı", list(DBS))
    preset = st.selectbox("Yapılandırma", list(PRESETS), index=list(PRESETS).index("full"),
                          help="Ablasyondaki kümülatif özellik setleri; 'full' hepsini açar.")
    st.caption("Yalnızca SELECT çalışır; salt okunur bağlantı, 100 satır sınırı, 5 sn zaman aşımı, "
               "telefon/adres gibi kolonlar gizli.")
    if st.button("Sohbeti temizle"):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.caption("Örnek sorular")
    for ex in EXAMPLES:
        if st.button(ex, use_container_width=True):
            st.session_state.pending = ex

st.session_state.setdefault("messages", [])
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m["role"] == "assistant":
            render_assistant(m)
        else:
            st.markdown(m["content"])

question = st.chat_input("Veritabanına bir soru sorun") or st.session_state.pop("pending", None)
if question:
    history = [{"q": m["standalone"], "sql": m["sql"]} for m in st.session_state.messages
              if m["role"] == "assistant" and m.get("sql")]
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Sorgu hazırlanıyor..."):
            try:
                out = get_graph(preset, DBS[db_label]).invoke({"question": question, "history": history})
                cols, rows = out.get("columns", []), out.get("rows", [])
                msg = {
                    "role": "assistant", "content": out.get("answer") or "Sonuç bulunamadı.",
                    "sql": out.get("sql", "") if not out.get("abstain") else "", "standalone": out["standalone"],
                    "abstain": out.get("abstain", ""), "blocked": out.get("blocked", False) and bool(out.get("error")),
                    "df": pd.DataFrame(rows, columns=cols) if rows and not out.get("error") else None,
                    "meta": f"{out['attempts']} deneme · {out['tokens']} token · {len(rows)} satır",
                }
            except Exception as e:  # keep the chat alive on API/network failures
                msg = {"role": "assistant", "content": f"Bir hata oluştu: {e}", "sql": "", "standalone": question}
        render_assistant(msg)
    st.session_state.messages.append(msg)
