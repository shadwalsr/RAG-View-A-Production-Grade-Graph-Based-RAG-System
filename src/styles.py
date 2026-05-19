"""Minimal CSS for RAG-VIEW dashboard."""

FONTS_AND_ICONS = """
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Bebas+Neue&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
"""

GLOBAL_CSS = """
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"],
.main, .block-container {
    background-color: #0A0D14 !important;
    color: #e1e2ec !important;
    font-family: 'Outfit', sans-serif !important;
}
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] { display: none !important; }

/* Remove ALL Streamlit default padding/margin */
.block-container {
    padding: 0 !important;
    padding-top: 0 !important;
    margin-top: 0 !important;
    max-width: 100% !important;
}
[data-testid="stApp"] > div:first-child { padding-top: 0 !important; }
.stApp { padding-top: 0 !important; }
/* Hide default Streamlit header bar */
[data-testid="stHeader"] { display: none !important; }
/* Kill the element-container gap Streamlit wraps everything in */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
    padding: 0 !important;
    margin: 0 !important;
}

.stTextInput > div > div > input {
    background-color: #101520 !important;
    border: 1px solid #1F2937 !important;
    color: #e1e2ec !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 14px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #00E5B5 !important;
    box-shadow: 0 0 0 1px #00E5B5 !important;
}
.stTextInput > div > div > input::placeholder { color: #6B7280 !important; }

.stButton > button {
    background-color: transparent !important;
    color: #00E5B5 !important;
    border: 1px solid #1F2937 !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    padding: 8px 20px !important;
    font-size: 13px !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    border-color: #00E5B5 !important;
    background-color: rgba(0,229,181,0.05) !important;
}

/* Tab menu. */
[data-testid="stRadio"],
[data-testid="stRadio"] > div,
[data-testid="stRadio"] > div > div,
[data-testid="stRadio"] > div > div > div[role="radiogroup"] {
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
    background: transparent !important;
    border: none !important;
}
[data-testid="stRadio"] > div > div[role="radiogroup"] {
    gap: 12px !important;
}
[data-testid="stRadio"] label {
    background: transparent !important;
    color: #4B5563 !important;
    padding: 10px 18px !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    white-space: nowrap !important;
}
[data-testid="stRadio"] label:hover {
    color: #9CA3AF !important;
}
[data-testid="stRadio"] label[data-checked="true"],
[data-testid="stRadio"] label:has(input:checked) {
    color: #e1e2ec !important;
    font-weight: 600 !important;
    background: transparent !important;
    border-bottom: 2px solid #00E5B5 !important;
}
[data-testid="stRadio"] input[type="radio"],
[data-testid="stRadio"] > label:first-child,
[data-testid="stRadio"] [data-baseweb="radio"] > div:first-child { display: none !important; }

.stFileUploader [data-testid="stFileUploaderDropzone"] {
    background: #101520 !important;
    border: 1px dashed #1F2937 !important;
    border-radius: 10px !important;
}
.stFileUploader [data-testid="stFileUploaderDropzone"]:hover {
    border-color: #00E5B5 !important;
}

[data-testid="stHorizontalBlock"] { gap: 20px !important; }
hr { border-color: #1F2937 !important; }

/* Remove Streamlit's auto-added empty top space */
[data-testid="stAppViewBlockContainer"] {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
/* Collapse the spacing Streamlit adds around markdown blocks */
.element-container { margin: 0 !important; padding: 0 !important; }
</style>
"""

