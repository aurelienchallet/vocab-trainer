import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Vocab Trainer", layout="centered")

st.title("📚 Vocabulary Trainer")

# Charger le CSV
df = pd.read_csv("vocab.csv")

# Nettoyage
df = df.dropna(subset=["word", "translation"])

# Initialisation session
if "score" not in st.session_state:
    st.session_state.score = 0
    st.session_state.total = 0
    st.session_state.word = df.sample(1).iloc[0]

# Affichage mot
st.subheader("Translate this word:")
st.write(f"👉 **{st.session_state.word['word']}**")

# Input
answer = st.text_input("Your answer:")

col1, col2 = st.columns(2)

# Vérifier
with col1:
    if st.button("Check"):
        correct = str(st.session_state.word["translation"]).lower().strip()
        user = answer.lower().strip()

        st.session_state.total += 1

        if user == correct:
            st.success("✅ Correct")
            st.session_state.score += 1
        else:
            st.error(f"❌ Wrong → {correct}")

# Mot suivant
with col2:
    if st.button("Next"):
        st.session_state.word = df.sample(1).iloc[0]
        st.rerun()

# Score
st.markdown("---")
st.write(f"Score: **{st.session_state.score} / {st.session_state.total}**")
