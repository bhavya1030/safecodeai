import ast
import re
import streamlit as st
import pickle
import datetime
from streamlit_ace import st_ace

from src.predict import review_code


# ─────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="SafeCodeAI – Code Reviewer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ─────────────────────────────────────────
#  GLOBAL CSS  (matches code.html design)
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

.material-symbols-outlined {
    font-family: 'Material Symbols Outlined';
    font-weight: normal; font-style: normal;
    font-size: inherit; line-height: 1;
    letter-spacing: normal; text-transform: none;
    display: inline-block; white-space: nowrap;
    direction: ltr; -webkit-font-smoothing: antialiased;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background: #101622 !important;
    color: #e2e8f0 !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

[data-testid="stSidebar"] {
    background: #101622 !important;
    border-right: 1px solid #2d3a54 !important;
    padding: 0 !important;
    min-width: 272px !important;
    max-width: 272px !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2d3a54; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #3d4d6e; }

.stButton > button {
    background: transparent !important; border: none !important;
    padding: 0 !important; font-family: 'Space Grotesk', sans-serif !important;
}
.stButton > button:focus { box-shadow: none !important; }
[data-testid="stMetric"] { display: none; }
[data-testid="stAlert"] { display: none; }
[data-testid="stFileUploader"] { display: none; }
[data-testid="stHorizontalBlock"] { gap: 0 !important; padding: 0 !important; }

/* ── NAV BAR ── */
.nav-bar {
    display: flex; align-items: center; justify-content: space-between;
    background: #101622; border-bottom: 1px solid #2d3a54;
    padding: 0 24px; height: 56px;
    position: sticky; top: 0; z-index: 999;
}
.nav-logo { display: flex; align-items: center; gap: 8px; font-size: 20px; font-weight: 700; color: #135bec; }
.nav-logo .material-symbols-outlined { font-size: 28px; }
.nav-links { display: flex; align-items: center; gap: 24px; margin-left: 40px; }
.nav-link { font-size: 14px; font-weight: 500; color: #94a3b8; text-decoration: none; padding-bottom: 4px; }
.nav-link.active { color: #135bec; border-bottom: 2px solid #135bec; }
.nav-right { display: flex; align-items: center; gap: 16px; }
.nav-badge {
    background: rgba(19,91,236,0.1); color: #135bec;
    font-size: 10px; font-weight: 700; padding: 3px 10px; border-radius: 4px; letter-spacing: .05em;
}
.nav-avatar {
    width: 36px; height: 36px;
    background: rgba(19,91,236,0.2); border: 1px solid rgba(19,91,236,0.3);
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700; color: #135bec;
}

/* ── SIDEBAR ── */
.sidebar-inner { padding: 16px; }
.sidebar-search {
    display: flex; align-items: center; gap: 8px;
    background: #1a2234; border-radius: 8px;
    padding: 8px 12px; margin-bottom: 20px; color: #94a3b8; font-size: 14px;
}
.sidebar-search .material-symbols-outlined { font-size: 18px; }
.sidebar-label {
    font-size: 10px; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: #64748b; margin-bottom: 8px; padding-left: 8px;
}
.session-card {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 12px; border-radius: 8px;
    margin-bottom: 2px; color: #94a3b8;
    border: 1px solid transparent;
}
.session-card.active { background: rgba(19,91,236,0.1); border-color: rgba(19,91,236,0.2); color: #135bec; }
.session-card .material-symbols-outlined { font-size: 20px; flex-shrink: 0; }
.session-info { flex: 1; min-width: 0; }
.session-name { font-size: 13px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.session-meta { font-size: 11px; opacity: .7; margin-top: 1px; }

/* sidebar select buttons – styled as small links */
[data-testid="stSidebar"] [data-testid="stButton"] > button {
    display: inline-flex !important;
    font-size: 10px !important; color: #135bec !important;
    font-weight: 600 !important; padding: 2px 6px !important;
    border-radius: 4px !important;
    border: 1px solid rgba(19,91,236,0.2) !important;
    background: rgba(19,91,236,0.06) !important;
    margin-top: -2px !important;
    font-family: 'Space Grotesk', sans-serif !important;
}
[data-testid="stSidebar"] [data-testid="stButton"]:last-of-type > button {
    display: flex !important; align-items: center !important; justify-content: center !important;
    background: #135bec !important; color: white !important;
    font-weight: 700 !important; font-size: 14px !important;
    padding: 10px !important; border-radius: 8px !important;
    width: 100% !important; border: none !important;
    font-family: 'Space Grotesk', sans-serif !important;
    margin-top: 8px !important;
}

/* ── TAB BAR ── */
.tab-bar {
    display: flex; align-items: center; justify-content: space-between;
    background: rgba(26,34,52,0.5); border-bottom: 1px solid #2d3a54;
    padding: 0 16px; height: 44px;
}
.tab {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 0 14px; height: 44px;
    font-size: 13px; font-weight: 500;
    color: #135bec; background: #101622;
    border-top: 2px solid #135bec; border-radius: 8px 8px 0 0;
}
.tab .material-symbols-outlined { font-size: 15px; }

/* Review button inside tab bar (styled st.button) */
div[data-testid="stButton"] > button[kind="primary"] {
    display: inline-flex !important; align-items: center !important; gap: 6px !important;
    padding: 6px 18px !important;
    background: rgba(34,197,94,0.1) !important; color: #22c55e !important;
    border: 1px solid rgba(34,197,94,0.25) !important;
    border-radius: 6px !important; font-size: 12px !important; font-weight: 700 !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

/* ── DROPZONE ── */
.dropzone {
    margin: 20px 20px 0 20px;
    border: 2px dashed rgba(255,255,255,0.1);
    border-radius: 12px; padding: 28px 20px;
    text-align: center; color: #94a3b8; font-size: 14px;
    transition: border-color .2s;
}
.dropzone:hover { border-color: rgba(19,91,236,0.5); }
.dz-icon-wrap {
    width: 48px; height: 48px;
    background: rgba(19,91,236,0.1); border-radius: 50%;
    display: flex; align-items: center; justify-content: center; margin: 0 auto 14px;
}
.dz-icon-wrap .material-symbols-outlined { font-size: 26px; color: #135bec; }
.dropzone a { color: #135bec; text-decoration: none; }
.dropzone-sub { font-size: 12px; margin-top: 4px; color: #64748b; }

/* ── STATUS BAR ── */
.status-bar {
    background: rgba(26,34,52,0.5); border-top: 1px solid #2d3a54;
    padding: 5px 16px;
    display: flex; align-items: center; justify-content: space-between;
    font-size: 10px; color: #64748b; font-weight: 700;
    letter-spacing: .08em; text-transform: uppercase;
}
.sb-left { display: flex; align-items: center; gap: 16px; }
.sb-left span { display: flex; align-items: center; gap: 4px; }
.sb-left .material-symbols-outlined { font-size: 12px; }
.status-branch { color: #22c55e; }

/* ── RIGHT PANEL ── */
.panel-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px; border-bottom: 1px solid #2d3a54;
}
.panel-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; }
.panel-title .material-symbols-outlined { font-size: 20px; color: #135bec; }

/* ── ISSUE CARDS ── */
.issue-card { border-radius: 12px; padding: 16px; margin-bottom: 12px; }
.issue-card.critical { background: rgba(239,68,68,0.05);  border: 1px solid rgba(239,68,68,0.2); }
.issue-card.warning  { background: rgba(249,115,22,0.05); border: 1px solid rgba(249,115,22,0.2); }
.issue-card.tip      { background: rgba(59,130,246,0.05); border: 1px solid rgba(59,130,246,0.2); }
.issue-card.success  { background: rgba(34,197,94,0.05);  border: 1px solid rgba(34,197,94,0.2); }

.issue-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 8px; }
.issue-severity { display: flex; align-items: center; gap: 6px; font-size: 10px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
.issue-severity .material-symbols-outlined { font-size: 17px; }
.issue-severity.critical { color: #ef4444; }
.issue-severity.warning  { color: #f97316; }
.issue-severity.tip      { color: #3b82f6; }
.issue-severity.success  { color: #22c55e; }
.issue-line { font-size: 10px; color: #64748b; }
.issue-title { font-size: 14px; font-weight: 600; color: #e2e8f0; margin-bottom: 6px; }
.issue-desc  { font-size: 12px; color: #94a3b8; line-height: 1.6; margin-bottom: 12px; }
.issue-desc code { background: #1a2234; padding: 1px 5px; border-radius: 4px; font-family: 'Fira Code', monospace; font-size: 11px; }
.btn-fix {
    width: 100%; padding: 8px; border-radius: 8px;
    font-size: 12px; font-weight: 700; text-align: center;
    cursor: pointer; border: none; color: white;
}
.btn-fix.critical { background: #ef4444; }
.btn-fix.warning  { background: #f97316; }
.btn-fix.tip      { background: #3b82f6; }

/* ── STAT CARDS ── */
.stat-row { display: flex; gap: 8px; margin-bottom: 16px; }
.stat-card { flex: 1; background: #1a2234; border: 1px solid #2d3a54; border-radius: 8px; padding: 10px; text-align: center; }
.stat-card-val { font-size: 20px; font-weight: 700; color: #135bec; }
.stat-card-lbl { font-size: 10px; color: #64748b; margin-top: 2px; }

/* ── HEALTH BADGE ── */
.health-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 700; margin-bottom: 16px; }
.health-badge.healthy { background: rgba(34,197,94,0.1);  color: #22c55e; border: 1px solid rgba(34,197,94,0.25); }
.health-badge.risky   { background: rgba(249,115,22,0.1); color: #f97316; border: 1px solid rgba(249,115,22,0.25); }
.health-badge.critical{ background: rgba(239,68,68,0.1);  color: #ef4444; border: 1px solid rgba(239,68,68,0.25); }

/* ── SCORE SECTION ── */
.score-section { padding: 16px; background: rgba(19,91,236,0.05); border-top: 1px solid #2d3a54; }
.score-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.score-label { font-size: 12px; font-weight: 700; }
.score-bar { width: 100%; background: #2d3a54; height: 6px; border-radius: 9999px; overflow: hidden; }
.score-fill { height: 100%; border-radius: 9999px; }

.sep { height: 1px; background: #2d3a54; margin: 12px 0; }
.empty-state { text-align: center; padding: 48px 16px; color: #64748b; }
.empty-state .material-symbols-outlined { font-size: 44px; margin-bottom: 12px; display: block; }
.empty-state-text { font-size: 13px; line-height: 1.7; }
.ace_editor { font-family: 'Fira Code', monospace !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
#  LOAD MODEL
# ─────────────────────────────────────────
@st.cache_resource
def load_model():
    try:
        with open("bug_risk_model.pkl", "rb") as f:
            return pickle.load(f)
    except Exception:
        return None

model = load_model()


# ─────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "selected_run" not in st.session_state:
    st.session_state.selected_run = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = None


# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
def time_ago(dt: datetime.datetime) -> str:
    diff = datetime.datetime.now() - dt
    s = int(diff.total_seconds())
    if s < 60:    return "just now"
    if s < 3600:  return f"{s//60} min ago"
    if s < 86400: return f"{s//3600} hr ago"
    return f"{s//86400} day ago"

def severity_of(issue_type: str):
    crit = ["infinite loop", "syntax", "division by zero", "recursion"]
    warn = ["tle", "nested", "complexity", "sorting", "input inside"]
    for c in crit:
        if c in issue_type.lower(): return "critical"
    for w in warn:
        if w in issue_type.lower(): return "warning"
    return "tip"

def health_label(confidence, issue_count):
    if confidence > 70 or issue_count >= 3:
        return "critical", "🔴 Critical"
    elif confidence > 35 or issue_count >= 1:
        return "risky", "⚠️ Risky"
    else:
        return "healthy", "✅ Healthy"

def review_score(confidence, issue_count, syntax_err):
    if syntax_err: return 20
    base = max(0, 100 - int(confidence) - issue_count * 8)
    return max(10, min(99, base))

def score_color(s):
    if s >= 75: return "#22c55e"
    if s >= 50: return "#f97316"
    return "#ef4444"

SEVERITY_ICONS  = {"critical": "security",  "warning": "warning",  "tip": "lightbulb"}
SEVERITY_LABELS = {"critical": "Critical Security", "warning": "Potential Bug", "tip": "Refactor Tip"}


# ─────────────────────────────────────────
#  TOP NAV BAR
# ─────────────────────────────────────────
st.markdown("""
<div class="nav-bar">
  <div style="display:flex;align-items:center;">
    <div class="nav-logo">
      <span class="material-symbols-outlined">terminal</span>
      <span>SafeCodeAI</span>
    </div>
    <div class="nav-links">
      <a class="nav-link active" href="#">Reviewer</a>
      <a class="nav-link" href="#">Workspace</a>
      <a class="nav-link" href="#">Docs</a>
    </div>
  </div>
  <div class="nav-right">
    <span class="nav-badge">AI READY</span>
    <div class="nav-avatar">DA</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-inner">
      <div class="sidebar-search">
        <span class="material-symbols-outlined">search</span>
        <span style="color:#64748b;font-size:13px;">Search sessions...</span>
      </div>
    """, unsafe_allow_html=True)

    now = datetime.datetime.now()
    today_items, yesterday_items, older_items = [], [], []
    for i, item in enumerate(st.session_state.history):
        d = (now - item.get("ts", now)).days
        if d == 0:   today_items.append((i, item))
        elif d == 1: yesterday_items.append((i, item))
        else:        older_items.append((i, item))

    def render_session(i, item):
        is_active  = st.session_state.selected_run == i
        issues     = item.get("result", {}).get("issues", [])
        n_issues   = len(issues)
        meta       = time_ago(item.get("ts", now))
        meta      += f" · {n_issues} issue{'s' if n_issues!=1 else ''}" if n_issues else " · Fixed"
        fname      = item.get("filename", f"run_{i+1}.py")
        ac         = " active" if is_active else ""
        st.markdown(f"""
        <div class="session-card{ac}">
          <span class="material-symbols-outlined">history</span>
          <div class="session-info">
            <div class="session-name">{fname}</div>
            <div class="session-meta">{meta}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open", key=f"sel_{i}"):
            st.session_state.selected_run = i
            st.rerun()

    if today_items:
        st.markdown('<div class="sidebar-label">Today</div>', unsafe_allow_html=True)
        for i, item in reversed(today_items): render_session(i, item)
    if yesterday_items:
        st.markdown('<div class="sidebar-label" style="margin-top:16px;">Yesterday</div>', unsafe_allow_html=True)
        for i, item in reversed(yesterday_items): render_session(i, item)
    if older_items:
        st.markdown('<div class="sidebar-label" style="margin-top:16px;">Earlier</div>', unsafe_allow_html=True)
        for i, item in reversed(older_items): render_session(i, item)

    if not st.session_state.history:
        st.markdown("""
        <div class="empty-state" style="margin-top:32px;">
          <span class="material-symbols-outlined">folder_open</span>
          <div class="empty-state-text">No review sessions yet.<br>Upload code to get started.</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    if st.button("＋  New Review Session", key="new_sess_btn"):
        st.session_state.active_tab   = None
        st.session_state.selected_run = None
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────
#  MAIN COLUMNS
# ─────────────────────────────────────────
col_center, col_right = st.columns([3, 2])


# ─────────────────────────────────────────
#  CENTER PANEL
# ─────────────────────────────────────────
with col_center:
    curr_tab = st.session_state.active_tab or "untitled.py"

    # Tab bar (visual) + real review button
    st.markdown(f"""
    <div class="tab-bar">
      <div style="display:flex;align-items:center;gap:4px;">
        <div class="tab">
          <span class="material-symbols-outlined">code</span>
          {curr_tab}
          <span class="material-symbols-outlined" style="font-size:13px;color:#64748b;cursor:pointer;">close</span>
        </div>
        <span style="padding:6px;color:#64748b;cursor:pointer;">
          <span class="material-symbols-outlined" style="font-size:16px;">add</span>
        </span>
      </div>
      <!-- real button rendered below via Streamlit -->
    </div>
    """, unsafe_allow_html=True)

    btn_col, lang_col, _ = st.columns([2, 2, 8])
    with btn_col:
        analyze_btn = st.button("▶  Review Code", type="primary", key="analyze_btn")
    with lang_col:
        selected_lang_display = st.selectbox("Language", ["Python", "C++", "Java"], label_visibility="collapsed")
        lang_map = {"Python": "python", "C++": "cpp", "Java": "java"}
        ace_lang_map = {"Python": "python", "C++": "c_cpp", "Java": "java"}

    # Drop zone (visual)
    st.markdown("""
    <div class="dropzone">
      <div class="dz-icon-wrap">
        <span class="material-symbols-outlined">upload_file</span>
      </div>
      <div>Drop code files here or <a href="#">browse files</a></div>
      <div class="dropzone-sub">Supports Python, C++, and Java files (.py, .cpp, .java)</div>
    </div>
    """, unsafe_allow_html=True)

    # Hidden real uploader
    uploaded_files = st.file_uploader(
        "Upload", type=["py", "cpp", "java"], accept_multiple_files=True,
        label_visibility="collapsed"
    )

    # ACE editor
    code_input = st_ace(
        language=ace_lang_map.get(selected_lang_display, "python"),
        theme="tomorrow_night",
        font_size=14,
        tab_size=4,
        show_gutter=True,
        wrap=False,
        height=460,
        key="code_ace",
        placeholder="# Paste your Python code here…\n"
    )

    line_count = len((code_input or "").splitlines())
    st.markdown(f"""
    <div class="status-bar">
      <div class="sb-left">
        <span><span class="material-symbols-outlined">info</span> UTF-8</span>
        <span><span class="material-symbols-outlined">code</span> {selected_lang_display}</span>
      </div>
      <div style="display:flex;align-items:center;gap:16px;">
        <span>Line {max(line_count, 1)}, Col 1</span>
        <span class="status-branch">Master Branch</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────
#  ANALYSIS LOGIC
# ─────────────────────────────────────────
if analyze_btn:
    codes, filenames = [], []
    if uploaded_files:
        for f in uploaded_files:
            codes.append(f.read().decode("utf-8"))
            filenames.append(f.name)
    elif code_input and code_input.strip():
        codes.append(code_input)
        filenames.append("editor_snippet.py")

    if codes:
        for code, fname in zip(codes, filenames):
            ext = fname.split(".")[-1].lower() if "." in fname else ""
            if ext in ["cpp", "cc", "cxx"]:
                code_lang = "cpp"
            elif ext == "java":
                code_lang = "java"
            elif ext == "py":
                code_lang = "python"
            else:
                code_lang = lang_map.get(selected_lang_display, "python")

            result = review_code(code, model, language=code_lang)
            st.session_state.history.append({
                "code": code, "result": result,
                "filename": fname, "ts": datetime.datetime.now(),
                "language": code_lang
            })
        st.session_state.selected_run = len(st.session_state.history) - 1
        st.session_state.active_tab   = filenames[-1]
        st.rerun()


# ─────────────────────────────────────────
#  RIGHT PANEL — REVIEW INSIGHTS
# ─────────────────────────────────────────
with col_right:
    st.markdown("""
    <div class="panel-header">
      <div class="panel-title">
        <span class="material-symbols-outlined">analytics</span>
        Review Insights
      </div>
      <span class="nav-badge">AI READY</span>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.selected_run is not None and st.session_state.history:
        item   = st.session_state.history[st.session_state.selected_run]
        result = item["result"]
        code   = item["code"]

        conf     = result.get("confidence", 0)
        issues   = result.get("issues", [])
        synerr   = result.get("syntax_error", False)
        err_line = result.get("error_line", "?")
        err_msg  = result.get("error_msg", "")
        loops    = result.get("complexity", 1)
        n_issues = len(issues) + (1 if synerr else 0)
        h_class, h_label = health_label(conf, n_issues)
        score    = review_score(conf, n_issues, synerr)
        sc       = score_color(score)

        review_lang = item.get("language", "python")
        if review_lang == "python":
            try:
                _tree = ast.parse(code)
                n_funcs = sum(isinstance(n, ast.FunctionDef) for n in ast.walk(_tree))
            except Exception:
                n_funcs = 0
        else:
            n_funcs = len(
                re.findall(
                    r"^\s*(?:[\w:<>\[\],*&]+\s+)+[A-Za-z_]\w*\s*\([^;{}]*\)\s*(?:\{|$)",
                    code,
                    flags=re.M,
                )
            )
        lines = len(code.splitlines())

        st.markdown(f"""
        <div style="padding:16px;">
          <div class="health-badge {h_class}">{h_label}</div>
          <div class="stat-row">
            <div class="stat-card"><div class="stat-card-val">{lines}</div><div class="stat-card-lbl">Lines</div></div>
            <div class="stat-card"><div class="stat-card-val">{n_funcs}</div><div class="stat-card-lbl">Functions</div></div>
            <div class="stat-card"><div class="stat-card-val">{loops}</div><div class="stat-card-lbl">Loops</div></div>
            <div class="stat-card"><div class="stat-card-val">{round(conf):.0f}%</div><div class="stat-card-lbl">Bug Risk</div></div>
          </div>
          <div class="sep"></div>
        """, unsafe_allow_html=True)

        # Syntax error card
        if synerr:
            st.markdown(f"""
            <div class="issue-card critical">
              <div class="issue-header">
                <div class="issue-severity critical">
                  <span class="material-symbols-outlined">security</span> Critical Security
                </div>
                <span class="issue-line">Line {err_line}</span>
              </div>
              <div class="issue-title">Syntax Error Detected</div>
              <div class="issue-desc">Code cannot be executed. <code>{err_msg}</code></div>
              <button class="btn-fix critical">Fix Syntax</button>
            </div>
            """, unsafe_allow_html=True)

        # Issue cards
        for issue_name, line_no, fix_text in issues:
            sev      = severity_of(issue_name)
            icon     = SEVERITY_ICONS.get(sev, "lightbulb")
            label    = SEVERITY_LABELS.get(sev, "Refactor Tip")
            line_str = f"Line {line_no}" if line_no else "Global"
            st.markdown(f"""
            <div class="issue-card {sev}">
              <div class="issue-header">
                <div class="issue-severity {sev}">
                  <span class="material-symbols-outlined">{icon}</span> {label}
                </div>
                <span class="issue-line">{line_str}</span>
              </div>
              <div class="issue-title">{issue_name}</div>
              <div class="issue-desc">{fix_text}</div>
              <button class="btn-fix {sev}">View Fix</button>
            </div>
            """, unsafe_allow_html=True)
            with st.expander("💡 Fix Suggestion", expanded=False):
                st.code(fix_text, language="python")

        if not issues and not synerr:
            st.markdown("""
            <div class="issue-card success">
              <div class="issue-header">
                <div class="issue-severity success">
                  <span class="material-symbols-outlined">check_circle</span> All Clear
                </div>
              </div>
              <div class="issue-title">No issues detected</div>
              <div class="issue-desc">Your code passed all static analysis checks. Great work!</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # Score pinned at bottom
        st.markdown(f"""
        <div class="score-section">
          <div class="score-header">
            <span class="score-label">Review Score</span>
            <span style="font-size:12px;font-weight:700;color:{sc};">{score} / 100</span>
          </div>
          <div class="score-bar">
            <div class="score-fill" style="width:{score}%;background:{sc};"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="empty-state" style="margin-top:60px;">
          <span class="material-symbols-outlined">shield</span>
          <div class="empty-state-text">
            No code reviewed yet.<br>
            Paste your Python code in the editor<br>and click <b>Review Code</b> to begin.
          </div>
        </div>
        """, unsafe_allow_html=True)
