import streamlit as st
import pandas as pd
import random
import unicodedata
from datetime import date, timedelta
from pathlib import Path

# =========================
# CONFIG
# =========================

st.set_page_config(
    page_title="English Vocabulary Trainer",
    page_icon="📚",
    layout="wide"
)

CSV_PATH = Path("vocab.csv")
PROGRESS_PATH = Path("progress.csv")


# =========================
# STYLE
# =========================

st.markdown("""
<style>
.main {
    background-color: #f8fafc;
}

.hero {
    padding: 35px;
    border-radius: 24px;
    background: linear-gradient(135deg, #0f172a, #1e3a8a);
    color: white;
    margin-bottom: 25px;
}

.hero h1 {
    font-size: 42px;
    margin-bottom: 10px;
}

.card {
    padding: 25px;
    border-radius: 20px;
    background-color: white;
    box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08);
    margin-bottom: 20px;
}

.word-card {
    padding: 45px;
    border-radius: 24px;
    background-color: white;
    text-align: center;
    box-shadow: 0 8px 25px rgba(15, 23, 42, 0.10);
    margin-top: 20px;
    margin-bottom: 20px;
}

.word {
    font-size: 46px;
    font-weight: 700;
    color: #0f172a;
}

.subtle {
    color: #64748b;
    font-size: 15px;
}

.badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    background-color: #e0f2fe;
    color: #0369a1;
    font-size: 13px;
    font-weight: 600;
    margin-right: 6px;
}
</style>
""", unsafe_allow_html=True)


# =========================
# HELPERS
# =========================

@st.cache_data
def load_vocab():
    df = pd.read_csv(CSV_PATH)

    df.columns = df.columns.str.strip().str.lower()

    required_cols = ["id", "english", "part_of_speech", "level", "translation_fr", "family"]
    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        st.error(f"Colonnes manquantes dans le CSV : {missing}")
        st.stop()

    df = df.dropna(subset=["english", "translation_fr"])
    df["id"] = df["id"].astype(str)
    df["english"] = df["english"].astype(str)
    df["translation_fr"] = df["translation_fr"].astype(str)
    df["part_of_speech"] = df["part_of_speech"].fillna("unknown").astype(str)
    df["level"] = df["level"].fillna("unknown").astype(str)
    df["family"] = df["family"].fillna("general").astype(str)

    return df


def load_progress():
    if PROGRESS_PATH.exists():
        progress = pd.read_csv(PROGRESS_PATH)
        progress["id"] = progress["id"].astype(str)
        return progress

    return pd.DataFrame(columns=[
        "id",
        "seen_count",
        "correct_count",
        "wrong_count",
        "status",
        "last_seen",
        "next_review"
    ])


def save_progress(progress):
    progress.to_csv(PROGRESS_PATH, index=False)


def normalize(text):
    text = str(text).lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def is_correct(user_answer, expected):
    user = normalize(user_answer)
    expected_norm = normalize(expected)

    possible_answers = [
        x.strip()
        for x in expected_norm.replace("/", ",").split(",")
        if x.strip()
    ]

    return user in possible_answers or user == expected_norm


def update_progress(progress, item_id, correct):
    today = date.today()

    if item_id in progress["id"].astype(str).values:
        idx = progress.index[progress["id"].astype(str) == item_id][0]
    else:
        progress.loc[len(progress)] = [
            item_id,
            0,
            0,
            0,
            "new",
            "",
            today.isoformat()
        ]
        idx = progress.index[-1]

    progress.loc[idx, "seen_count"] = int(progress.loc[idx, "seen_count"]) + 1
    progress.loc[idx, "last_seen"] = today.isoformat()

    if correct:
        progress.loc[idx, "correct_count"] = int(progress.loc[idx, "correct_count"]) + 1
        correct_count = int(progress.loc[idx, "correct_count"])

        intervals = {
            1: 1,
            2: 3,
            3: 7,
            4: 14,
            5: 30
        }

        days = intervals.get(correct_count, 30)
        progress.loc[idx, "next_review"] = (today + timedelta(days=days)).isoformat()

        if correct_count >= 5:
            progress.loc[idx, "status"] = "mastered"
        else:
            progress.loc[idx, "status"] = "review"

    else:
        progress.loc[idx, "wrong_count"] = int(progress.loc[idx, "wrong_count"]) + 1
        progress.loc[idx, "next_review"] = today.isoformat()

        if int(progress.loc[idx, "wrong_count"]) >= 2:
            progress.loc[idx, "status"] = "difficult"
        else:
            progress.loc[idx, "status"] = "learning"

    return progress


def filter_vocab(df, level, word_type, family):
    filtered = df.copy()

    if level != "All":
        filtered = filtered[filtered["level"] == level]

    if word_type != "All":
        filtered = filtered[filtered["part_of_speech"] == word_type]

    if family != "All":
        filtered = filtered[filtered["family"] == family]

    return filtered


# =========================
# DATA
# =========================

vocab = load_vocab()
progress = load_progress()

merged = vocab.merge(progress, on="id", how="left")
merged["seen_count"] = merged["seen_count"].fillna(0)
merged["correct_count"] = merged["correct_count"].fillna(0)
merged["wrong_count"] = merged["wrong_count"].fillna(0)
merged["status"] = merged["status"].fillna("new")


# =========================
# SIDEBAR
# =========================

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Choose a page",
    ["Home", "Training", "Quiz", "Progression", "Difficult Words"]
)

st.sidebar.divider()

st.sidebar.caption("Dataset")
st.sidebar.write(f"{len(vocab)} entries loaded")


# =========================
# HOME
# =========================

if page == "Home":
    st.markdown("""
    <div class="hero">
        <h1>English Vocabulary Trainer</h1>
        <p>Train English vocabulary, verbs and phrasal verbs with quizzes, categories and progress tracking.</p>
    </div>
    """, unsafe_allow_html=True)

    total = len(merged)
    seen = int((merged["seen_count"] > 0).sum())
    mastered = int((merged["status"] == "mastered").sum())
    difficult = int((merged["status"] == "difficult").sum())

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total words", total)
    col2.metric("Seen", seen)
    col3.metric("Mastered", mastered)
    col4.metric("Difficult", difficult)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("What this app does")
    st.write("""
    This app helps you train English vocabulary in a structured way:
    
    1. Training mode to revise freely by level, type and family.
    2. Quiz mode with adaptive tracking.
    3. Progression dashboard to monitor your results.
    4. Difficult words page to focus on weaknesses.
    """)
    st.markdown('</div>', unsafe_allow_html=True)



# =========================
# TRAINING
# =========================

elif page == "Training":

    import random

    st.title("English Vocabulary Training")

    # --- Liste de mots ---
    if "words" not in st.session_state:
        st.session_state.words = [
            {"english": "achieve", "french": "atteindre"},
            {"english": "improve", "french": "améliorer"},
            {"english": "increase", "french": "augmenter"},
            {"english": "decrease", "french": "diminuer"},
        ]

    words = st.session_state.words

    # --- États ---
    if "show_translation" not in st.session_state:
        st.session_state.show_translation = False

    if "current_word_index" not in st.session_state:
        st.session_state.current_word_index = random.randint(0, len(words) - 1)

    current_word = words[st.session_state.current_word_index]

    # --- Style carte centrée ---
    st.markdown("""
    <style>
    div.stButton > button {
        width: 420px;
        height: 230px;
        display: block;
        margin: 50px auto;
        border-radius: 24px;
        font-size: 36px;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- Texte carte ---
    if st.session_state.show_translation:
        card_text = current_word["french"]
    else:
        card_text = current_word["english"]

    # --- Carte (flip) ---
    if st.button(card_text, key="card_button"):
        st.session_state.show_translation = not st.session_state.show_translation
        st.rerun()

    # --- Next word ---
    if st.button("Next word", key="next_word_button"):

        new_index = random.randint(0, len(words) - 1)

        while new_index == st.session_state.current_word_index and len(words) > 1:
            new_index = random.randint(0, len(words) - 1)

        st.session_state.current_word_index = new_index
        st.session_state.show_translation = False
        st.rerun()
# =========================
# QUIZ
# =========================

elif page == "Quiz":
    st.title("Quiz Mode")

    col1, col2, col3 = st.columns(3)

    with col1:
        level = st.selectbox("Level", ["All"] + sorted(vocab["level"].unique()), key="quiz_level")

    with col2:
        word_type = st.selectbox("Type", ["All"] + sorted(vocab["part_of_speech"].unique()), key="quiz_type")

    with col3:
        family = st.selectbox("Family", ["All"] + sorted(vocab["family"].unique()), key="quiz_family")

    quiz_size = st.slider("Number of questions", 5, 50, 20, 5)

    direction = st.radio(
        "Direction",
        ["English → French", "French → English"],
        horizontal=True,
        key="quiz_direction"
    )

    quiz_pool = filter_vocab(vocab, level, word_type, family)

    if len(quiz_pool) == 0:
        st.warning("No words found with these filters.")
        st.stop()

    if "quiz_items" not in st.session_state:
        st.session_state.quiz_items = []
        st.session_state.quiz_index = 0
        st.session_state.quiz_score = 0
        st.session_state.checked = False
        st.session_state.current_answer = ""

    if st.button("Start new quiz"):
        sample_size = min(quiz_size, len(quiz_pool))
        st.session_state.quiz_items = quiz_pool.sample(sample_size).to_dict("records")
        st.session_state.quiz_index = 0
        st.session_state.quiz_score = 0
        st.session_state.checked = False
        st.session_state.current_answer = ""
        st.rerun()

    if not st.session_state.quiz_items:
        st.info("Click Start new quiz.")
        st.stop()

    items = st.session_state.quiz_items
    idx = st.session_state.quiz_index

    if idx >= len(items):
        st.success(f"Quiz finished. Score: {st.session_state.quiz_score}/{len(items)}")
        if st.button("Restart"):
            st.session_state.quiz_items = []
            st.rerun()
        st.stop()

    item = items[idx]

    progress_ratio = idx / len(items)
    st.progress(progress_ratio)
    st.caption(f"Question {idx + 1} / {len(items)}")

    if direction == "English → French":
        question = item["english"]
        expected = item["translation_fr"]
    else:
        question = item["translation_fr"]
        expected = item["english"]

    st.markdown(f"""
    <div class="word-card">
        <div class="word">{question}</div>
        <br>
        <span class="badge">{item["part_of_speech"]}</span>
        <span class="badge">{item["level"]}</span>
        <span class="badge">{item["family"]}</span>
    </div>
    """, unsafe_allow_html=True)

    answer = st.text_input("Your answer", value=st.session_state.current_answer)

    col_check, col_next = st.columns(2)

    with col_check:
        if st.button("Check answer"):
            correct = is_correct(answer, expected)

            st.session_state.checked = True

            if correct:
                st.session_state.quiz_score += 1
                st.success("Correct")
            else:
                st.error("Incorrect")

            st.info(f"Correct answer: {expected}")

            progress = load_progress()
            progress = update_progress(progress, str(item["id"]), correct)
            save_progress(progress)

    with col_next:
        if st.button("Next"):
            st.session_state.quiz_index += 1
            st.session_state.checked = False
            st.session_state.current_answer = ""
            st.rerun()

    st.write(f"Score: **{st.session_state.quiz_score}/{idx + 1}**")


# =========================
# PROGRESSION
# =========================

elif page == "Progression":
    st.title("Progression")

    total = len(merged)
    seen = int((merged["seen_count"] > 0).sum())
    correct = int(merged["correct_count"].sum())
    wrong = int(merged["wrong_count"].sum())
    mastered = int((merged["status"] == "mastered").sum())
    difficult = int((merged["status"] == "difficult").sum())

    accuracy = correct / (correct + wrong) * 100 if (correct + wrong) > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total", total)
    col2.metric("Seen", seen)
    col3.metric("Correct", correct)
    col4.metric("Wrong", wrong)
    col5.metric("Accuracy", f"{accuracy:.1f}%")

    col6, col7 = st.columns(2)
    col6.metric("Mastered", mastered)
    col7.metric("Difficult", difficult)

    st.divider()

    st.subheader("Progress by family")

    family_stats = merged.groupby("family").agg(
        total=("id", "count"),
        seen=("seen_count", lambda x: int((x > 0).sum())),
        correct=("correct_count", "sum"),
        wrong=("wrong_count", "sum")
    ).reset_index()

    family_stats["progress_%"] = (family_stats["seen"] / family_stats["total"] * 100).round(1)

    st.dataframe(family_stats, use_container_width=True, hide_index=True)

    st.subheader("Progress by level")

    level_stats = merged.groupby("level").agg(
        total=("id", "count"),
        seen=("seen_count", lambda x: int((x > 0).sum())),
        correct=("correct_count", "sum"),
        wrong=("wrong_count", "sum")
    ).reset_index()

    level_stats["progress_%"] = (level_stats["seen"] / level_stats["total"] * 100).round(1)

    st.dataframe(level_stats, use_container_width=True, hide_index=True)

    if st.button("Reset all progress"):
        if PROGRESS_PATH.exists():
            PROGRESS_PATH.unlink()
        st.success("Progress reset. Refresh the page.")


# =========================
# DIFFICULT WORDS
# =========================

elif page == "Difficult Words":
    st.title("Difficult Words")

    difficult_words = merged[merged["status"] == "difficult"].copy()

    if len(difficult_words) == 0:
        st.success("No difficult words yet.")
    else:
        st.write(f"Words marked as difficult: **{len(difficult_words)}**")

        st.dataframe(
            difficult_words[
                ["english", "translation_fr", "part_of_speech", "level", "family", "wrong_count"]
            ],
            use_container_width=True,
            hide_index=True
        )
