import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import random

import sqlite3

# Page config must be the first Streamlit command
st.set_page_config(page_title="Carbon Premium Analytics", layout="wide", page_icon="🌍")

# --- Custom CSS for Likert Bubbles ---
st.markdown("""
<style>
/* Likert bubble styling — targets horizontal radio buttons */
div[data-testid="stHorizontalBlock"] div[role="radiogroup"] {
    display: flex;
    gap: 0.6rem;
    justify-content: center;
}
div[data-testid="stHorizontalBlock"] div[role="radiogroup"] label {
    background: #102A20;
    border: 2px solid #A7F3D0;
    border-radius: 50%;
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 1.1rem;
    cursor: pointer;
    transition: all 0.2s;
}
div[data-testid="stHorizontalBlock"] div[role="radiogroup"] label:hover {
    border-color: #00E676;
    background: #1a3d2e;
}
div[data-testid="stHorizontalBlock"] div[role="radiogroup"] label[data-checked="true"],
div[data-testid="stHorizontalBlock"] div[role="radiogroup"] label:has(input:checked) {
    background: #00E676;
    color: #0A1913;
    border-color: #00E676;
}
/* Hide the default radio circle */
div[data-testid="stHorizontalBlock"] div[role="radiogroup"] input[type="radio"] {
    display: none;
}
/* Likert scale labels row */
.likert-labels {
    display: flex;
    justify-content: space-between;
    color: #A7F3D0;
    font-size: 0.8rem;
    margin-top: -0.5rem;
    margin-bottom: 1rem;
    padding: 0 0.5rem;
}
</style>
""", unsafe_allow_html=True)

DB_FILE = "live_wtp_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method TEXT,
            env_score REAL,
            ladder_wtp REAL,
            dc_offer REAL,
            dc_vote TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- Matplotlib Model 1 Theme Configuration ---
TEXT_COLOR = "#FFFFFF"
AXIS_COLOR = "#A7F3D0"
PRIMARY_COLOR = "#00E676"
SECONDARY_COLOR = "#00B4D8"

plt.rcParams.update({
    "text.color": TEXT_COLOR,
    "axes.labelcolor": TEXT_COLOR,
    "axes.edgecolor": AXIS_COLOR,
    "xtick.color": AXIS_COLOR,
    "ytick.color": AXIS_COLOR,
    "font.family": "sans-serif",
    "axes.facecolor": "none",
    "figure.facecolor": "none"
})

def load_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM responses", conn)
    conn.close()
    return df

# --- Load Data ---
df = load_data()

# --- App Header ---
st.title("🌍 Carbon Premium: Live Market Simulation")
st.markdown("Welcome. We are assessing consumer willingness to absorb the **Green Premium** on a standard basket of goods.")

tabs = st.tabs(["📝 Consumer Questionnaire", "📊 Live Market Analytics (Dashboard)"])

# ==========================================
# TAB 1: QUESTIONNAIRE
# ==========================================
with tabs[0]:
    st.header("Step 1: Environmental Reliability (Cronbach's Setup)")
    st.markdown("To ensure data integrity, please rate your agreement with the following statements.")
    st.markdown('<div class="likert-labels"><span>1 — Strongly Disagree</span><span>2</span><span>3 — Neutral</span><span>4</span><span>5 — Strongly Agree</span></div>', unsafe_allow_html=True)
    
    st.markdown("**1. Corporations must take immediate action on climate change.**")
    q1 = st.radio("Q1", [1, 2, 3, 4, 5], index=2, horizontal=True, label_visibility="collapsed", key="q1")
    
    st.markdown("**2. I am willing to change my consumption habits to protect the environment.**")
    q2 = st.radio("Q2", [1, 2, 3, 4, 5], index=2, horizontal=True, label_visibility="collapsed", key="q2")
    
    env_score = (q1 + q2) / 2
    
    st.divider()
    
    st.header("Step 2: The Green Premium")
    st.markdown("""
    Imagine a **monthly basket of household goods and services** (Electricity, Groceries, Fuel). 
    The current base cost is **€500 / month**.
    """)
    
    # A/B Testing Assignment
    if "method" not in st.session_state:
        st.session_state.method = random.choice(["Ladder", "DC"])
        st.session_state.dc_offer = random.choice([10, 20, 50, 75, 100, 150, 200])

    method = st.session_state.method
    
    ladder_wtp = np.nan
    dc_vote = ""
    dc_offer = np.nan

    with st.container():
        st.info(f"**Live A/B Testing Active**: You have been randomly assigned to the **{method}** group.")
        
        if method == "Ladder":
            st.subheader("Method A: Payment Ladder")
            st.markdown("What is the **MAXIMUM extra amount** you would pay per month to ensure this entire basket is certified 100% Carbon Neutral?")
            options = [0, 10, 20, 30, 50, 75, 100, 150, 200, 250, 300]
            ladder_wtp = st.select_slider("Select your maximum premium (€):", options=options, value=0)
        
        else:
            st.subheader("Method B: Dichotomous Choice (Referendum)")
            dc_offer = st.session_state.dc_offer
            st.markdown(f"To make your €500 monthly basket 100% Carbon Neutral, it will cost an **additional €{dc_offer}**.")
            vote_input = st.radio("Would you accept this price increase?", ["(Select an option)", "Yes", "No"])
            if vote_input != "(Select an option)":
                dc_vote = vote_input

    st.write("")
    if st.button("Submit My Response", type="primary"):
        if method == "DC" and dc_vote == "":
            st.error("Please select Yes or No before submitting.")
        else:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''
                INSERT INTO responses (method, env_score, ladder_wtp, dc_offer, dc_vote)
                VALUES (?, ?, ?, ?, ?)
            ''', (method, env_score, ladder_wtp if pd.notna(ladder_wtp) else None, dc_offer if pd.notna(dc_offer) else None, dc_vote))
            conn.commit()
            conn.close()
            st.success("✅ Response recorded! Go to the **Live Market Analytics** tab to see your impact.")
            del st.session_state.method # Reset for next participant

# ==========================================
# TAB 2: LIVE ANALYTICS
# ==========================================
with tabs[1]:
    st.header("Live Corporate Dashboard")
    st.markdown(f"**Total Responses Analyzed:** {len(df)}")
    
    col1, col2 = st.columns(2)
    
    df_ladder = df[df["method"] == "Ladder"].dropna(subset=["ladder_wtp"])
    df_dc = df[df["method"] == "DC"].dropna(subset=["dc_vote"])
    
    # --- Plot 1: WTP Distribution (Ladder) ---
    with col1:
        st.subheader("True Demand Distribution (Method A)")
        if len(df_ladder) > 0:
            fig1, ax1 = plt.subplots(figsize=(8, 5))
            use_kde = len(df_ladder) > 2  # KDE needs several points
            bins = [0, 10, 20, 30, 50, 75, 100, 150, 200, 250, 300]
            sns.histplot(df_ladder["ladder_wtp"], bins=bins, kde=use_kde, color=PRIMARY_COLOR, ax=ax1, edgecolor="white", alpha=0.6)
            
            median_val = df_ladder["ladder_wtp"].median()
            ax1.axvline(median_val, color=SECONDARY_COLOR, linestyle='--', linewidth=3)
            ax1.text(median_val + 8, ax1.get_ylim()[1]*0.85, f'Median: €{int(median_val)}', color=SECONDARY_COLOR, fontsize=12, fontweight='bold')
            
            ax1.set_xlim(0, 310)
            ax1.set_ylim(bottom=0)
            ax1.set_xlabel('Max Willingness to Pay (€)', fontweight='bold')
            ax1.set_ylabel('Number of Consumers', fontweight='bold')
            ax1.spines['top'].set_visible(False)
            ax1.spines['right'].set_visible(False)
            ax1.grid(axis='y', linestyle='--', alpha=0.3, color=AXIS_COLOR)
            plt.tight_layout()
            st.pyplot(fig1)
        else:
            st.info("📊 Waiting for Method A responses...")

    # --- Plot 2: Demand Curve (DC) ---
    ALL_OFFERS = [10, 20, 50, 75, 100, 150, 200]
    with col2:
        st.subheader("Market Tolerance Curve (Method B)")
        if not df_dc.empty:
            # Build a full-range summary ensuring all offer levels appear
            dc_summary = df_dc.groupby(["dc_offer", "dc_vote"]).size().unstack(fill_value=0)
            if "Yes" not in dc_summary: dc_summary["Yes"] = 0
            if "No" not in dc_summary: dc_summary["No"] = 0
            
            # Reindex to include all possible offer values
            dc_summary = dc_summary.reindex(ALL_OFFERS, fill_value=0)
            dc_summary["total"] = dc_summary["Yes"] + dc_summary["No"]
            dc_summary["prop_yes"] = dc_summary.apply(
                lambda r: (r["Yes"] / r["total"] * 100) if r["total"] > 0 else np.nan, axis=1
            )
            
            # Only plot offers that actually have data
            plot_data = dc_summary.dropna(subset=["prop_yes"])
            
            fig2, ax2 = plt.subplots(figsize=(8, 5))
            ax2.plot(plot_data.index, plot_data["prop_yes"], marker='o', linestyle='-', linewidth=3, markersize=10, color=SECONDARY_COLOR, markeredgecolor='white', markeredgewidth=1.5)
            
            ax2.axhline(50, color='gray', linestyle='--', alpha=0.7)
            ax2.text(155, 53, "50% Market Acceptance", color='gray', fontsize=10, fontweight='bold')
            
            ax2.set_xlim(0, 220)
            ax2.set_ylim(0, 105)
            ax2.set_xticks(ALL_OFFERS)
            ax2.set_xlabel('Proposed Green Premium (€)', fontweight='bold')
            ax2.set_ylabel('Acceptance Rate (%)', fontweight='bold')
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            ax2.grid(axis='both', linestyle='--', alpha=0.3, color=AXIS_COLOR)
            plt.tight_layout()
            st.pyplot(fig2)
        else:
            st.info("📊 Waiting for Method B responses...")
            
    st.divider()
    
    # --- Plot 3: Framing Effect Comparison ---
    st.subheader("The Framing Effect: Anchor Bias in Pricing")
    st.markdown("Comparing the internal threshold (Median from Method A) against the psychological acceptance of a fixed price (Method B).")
    
    if not df_ladder.empty and not df_dc.empty:
        # Estimate DC "average" accepted. Simplistic approach for demo: average of all accepted offers.
        dc_accepted = df_dc[df_dc["dc_vote"] == "Yes"]["dc_offer"]
        dc_implied_mean = dc_accepted.mean() if not dc_accepted.empty else 0
        ladder_median = df_ladder["ladder_wtp"].median()
        
        fig3, ax3 = plt.subplots(figsize=(10, 4))
        labels = ['Method A\n(Consumer-Driven Median)', 'Method B\n(Average Accepted Anchor)']
        values = [ladder_median, dc_implied_mean]
        
        bars = ax3.barh(labels, values, color=[PRIMARY_COLOR, SECONDARY_COLOR], alpha=0.8, height=0.5)
        
        for bar in bars:
            width = bar.get_width()
            ax3.annotate(f'€{int(width)}',
                        xy=(width, bar.get_y() + bar.get_height() / 2),
                        xytext=(5, 0),
                        textcoords="offset points",
                        ha='left', va='center', fontsize=12, fontweight='bold', color=TEXT_COLOR)

        ax3.set_xlabel('Apparent Willingness to Pay (€)', fontweight='bold')
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
        ax3.spines['bottom'].set_visible(False)
        ax3.xaxis.set_ticks([]) # Hide x ticks for clean look
        st.pyplot(fig3)
    
    # Add a reset button for presenter
    if st.button("Reset Data (Start Fresh)"):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        st.rerun()

