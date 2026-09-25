import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import random
import sqlite3
from contextlib import contextmanager

# Page config must be the first Streamlit command
st.set_page_config(page_title="Carbon Premium Analytics", layout="wide", page_icon="🌍")

DB_FILE = "live_wtp_data.db"


@contextmanager
def get_conn():
    """Ensures the SQLite connection is always closed, even on error."""
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute('''
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


init_db()

# --- Matplotlib Theme Configuration ---
# Fixed dark background (instead of "none") so charts stay legible
# regardless of the viewer's Streamlit theme (light or dark).
BG_COLOR = "#0E1117"
TEXT_COLOR = "#FFFFFF"
AXIS_COLOR = "#A7F3D0"
PRIMARY_COLOR = "#00E676"
SECONDARY_COLOR = "#00B4D8"
GRID_COLOR = "#2A2F3A"

plt.rcParams.update({
    "text.color": TEXT_COLOR,
    "axes.labelcolor": TEXT_COLOR,
    "axes.edgecolor": AXIS_COLOR,
    "xtick.color": AXIS_COLOR,
    "ytick.color": AXIS_COLOR,
    "font.family": "sans-serif",
    "font.size": 12,
    "axes.titlesize": 14,
    "axes.labelsize": 13,
    "axes.facecolor": BG_COLOR,
    "figure.facecolor": BG_COLOR,
    "savefig.facecolor": BG_COLOR,
})


def style_axes(ax, top=True, right=True, bottom=False):
    """Removes clutter spines consistently across all charts."""
    ax.spines['top'].set_visible(not top)
    ax.spines['right'].set_visible(not right)
    if bottom:
        ax.spines['bottom'].set_visible(False)
    ax.grid(axis='y', color=GRID_COLOR, linewidth=0.8, alpha=0.6)
    ax.set_axisbelow(True)


def load_data():
    with get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM responses", conn)


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
    st.header("Step 1: Environmental Attitude Index")
    st.markdown(
        "Rate your agreement with the following statements (this is a simple 2-item "
        "attitude average, not a validated reliability scale):"
    )

    q1 = st.slider("1. Corporations must take immediate action on climate change.", 1, 5, 3)
    q2 = st.slider("2. I am willing to change my consumption habits to protect the environment.", 1, 5, 3)
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
            with get_conn() as conn:
                conn.execute('''
                    INSERT INTO responses (method, env_score, ladder_wtp, dc_offer, dc_vote)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    method,
                    env_score,
                    ladder_wtp if pd.notna(ladder_wtp) else None,
                    dc_offer if pd.notna(dc_offer) else None,
                    dc_vote,
                ))
                conn.commit()
            st.success("✅ Response recorded! Go to the **Live Market Analytics** tab to see your impact.")
            del st.session_state.method  # Reset for next participant

# ==========================================
# TAB 2: LIVE ANALYTICS
# ==========================================
with tabs[1]:
    st.header("Live Corporate Dashboard")

    df_ladder = df[df["method"] == "Ladder"].dropna(subset=["ladder_wtp"])
    df_dc = df[df["method"] == "DC"].dropna(subset=["dc_vote"])

    # --- Summary metrics ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Responses", len(df))
    m2.metric("Method A (Ladder) N", len(df_ladder))
    m3.metric("Method B (DC) N", len(df_dc))
    overall_accept = (df_dc["dc_vote"] == "Yes").mean() * 100 if len(df_dc) else 0
    m4.metric("DC Acceptance Rate", f"{overall_accept:.0f}%")

    st.divider()

    col1, col2 = st.columns(2)

    # --- Plot 1: WTP Distribution (Ladder) ---
    with col1:
        st.subheader("True Demand Distribution (Method A)")
        if len(df_ladder) > 0:
            fig1, ax1 = plt.subplots(figsize=(9, 6.5))
            use_kde = len(df_ladder) > 1  # KDE needs at least 2 points
            sns.histplot(df_ladder["ladder_wtp"], bins=10, kde=use_kde, color=PRIMARY_COLOR,
                         ax=ax1, edgecolor=BG_COLOR, alpha=0.75)

            median_val = df_ladder["ladder_wtp"].median()
            ax1.axvline(median_val, color=SECONDARY_COLOR, linestyle='--', linewidth=2.5)
            x_range = df_ladder["ladder_wtp"].max() - df_ladder["ladder_wtp"].min()
            x_offset = max(x_range * 0.03, 3)
            # Keep the label inside the axes even when the median sits near the right edge
            ha = 'left' if median_val + x_offset < ax1.get_xlim()[1] * 0.85 else 'right'
            x_text = median_val + x_offset if ha == 'left' else median_val - x_offset
            ax1.text(x_text, ax1.get_ylim()[1] * 0.92, f'Median: €{int(median_val)}',
                     color=SECONDARY_COLOR, fontsize=13, fontweight='bold', ha=ha)

            ax1.set_xlabel('Max Willingness to Pay (€)', fontweight='bold')
            ax1.set_ylabel('Number of Consumers', fontweight='bold')
            style_axes(ax1)
            fig1.tight_layout()
            st.pyplot(fig1, use_container_width=True)
        else:
            st.write("Waiting for data...")

    # --- Plot 2: Demand Curve (DC) ---
    with col2:
        st.subheader("Market Tolerance Curve (Method B)")
        if not df_dc.empty:
            dc_summary = df_dc.groupby(["dc_offer", "dc_vote"]).size().unstack(fill_value=0)
            if "Yes" not in dc_summary:
                dc_summary["Yes"] = 0
            if "No" not in dc_summary:
                dc_summary["No"] = 0

            dc_summary["total"] = dc_summary["Yes"] + dc_summary["No"]
            dc_summary["prop_yes"] = (dc_summary["Yes"] / dc_summary["total"]) * 100

            fig2, ax2 = plt.subplots(figsize=(9, 6.5))
            ax2.plot(dc_summary.index, dc_summary["prop_yes"], marker='o', linestyle='-',
                    linewidth=2.5, markersize=9, color=SECONDARY_COLOR)

            # Annotate sample size at each offer point so low-N points aren't over-trusted
            for offer, row in dc_summary.iterrows():
                ax2.annotate(f'n={int(row["total"])}', (offer, row["prop_yes"]),
                            textcoords="offset points", xytext=(0, 10),
                            ha='center', fontsize=9, color=AXIS_COLOR)

            ax2.axhline(50, color='gray', linestyle='--', alpha=0.7)
            ax2.text(ax2.get_xlim()[0] + (ax2.get_xlim()[1] - ax2.get_xlim()[0]) * 0.02, 53,
                     "50% Market Acceptance", color='gray', fontsize=10, fontweight='bold')

            ax2.set_xlabel('Proposed Green Premium (€)', fontweight='bold')
            ax2.set_ylabel('Acceptance Rate (%)', fontweight='bold')
            ax2.set_ylim(-5, 105)
            style_axes(ax2)
            fig2.tight_layout()
            st.pyplot(fig2, use_container_width=True)
        else:
            st.write("Waiting for data...")

    st.divider()

    # --- Plot 3: Framing Effect Comparison ---
    st.subheader("The Framing Effect: Anchor Bias in Pricing")
    st.markdown("Comparing the internal threshold (Median from Method A) against the psychological acceptance of a fixed price (Method B).")

    if not df_ladder.empty and not df_dc.empty:
        dc_accepted = df_dc[df_dc["dc_vote"] == "Yes"]["dc_offer"]
        dc_implied_mean = dc_accepted.mean() if not dc_accepted.empty else 0
        ladder_median = df_ladder["ladder_wtp"].median()

        fig3, ax3 = plt.subplots(figsize=(11, 4.5))
        labels = ['Method A\n(Consumer-Driven Median)', 'Method B\n(Average Accepted Anchor)']
        values = [ladder_median, dc_implied_mean]

        bars = ax3.barh(labels, values, color=[PRIMARY_COLOR, SECONDARY_COLOR], alpha=0.85, height=0.5)

        for bar in bars:
            width = bar.get_width()
            ax3.annotate(f'€{int(width)}',
                        xy=(width, bar.get_y() + bar.get_height() / 2),
                        xytext=(8, 0), textcoords="offset points",
                        ha='left', va='center', fontsize=13, fontweight='bold', color=TEXT_COLOR)

        ax3.set_xlabel('Apparent Willingness to Pay (€)', fontweight='bold')
        ax3.set_xlim(0, max(values) * 1.25 if max(values) > 0 else 10)
        style_axes(ax3, bottom=True)
        ax3.xaxis.set_ticks([])
        fig3.tight_layout()
        st.pyplot(fig3, use_container_width=True)

    st.divider()

    # --- Plot 4: Does environmental attitude predict WTP? ---
    st.subheader("Does Environmental Attitude Predict Willingness to Pay?")
    st.markdown("This is the core behavioral question: do stronger pro-environmental attitudes translate into higher WTP?")

    col3, col4 = st.columns(2)

    with col3:
        if len(df_ladder) > 1:
            fig4, ax4 = plt.subplots(figsize=(9, 6))
            ax4.scatter(df_ladder["env_score"], df_ladder["ladder_wtp"],
                       color=PRIMARY_COLOR, s=80, alpha=0.75, edgecolor=BG_COLOR)

            # Simple linear trend line
            z = np.polyfit(df_ladder["env_score"], df_ladder["ladder_wtp"], 1)
            x_line = np.linspace(df_ladder["env_score"].min(), df_ladder["env_score"].max(), 50)
            ax4.plot(x_line, np.polyval(z, x_line), color=SECONDARY_COLOR, linewidth=2, linestyle='--')

            corr = df_ladder["env_score"].corr(df_ladder["ladder_wtp"])
            ax4.set_title(f"Method A — Pearson r = {corr:.2f}", fontsize=12)
            ax4.set_xlabel('Environmental Attitude Index (1-5)', fontweight='bold')
            ax4.set_ylabel('Max WTP (€)', fontweight='bold')
            style_axes(ax4)
            fig4.tight_layout()
            st.pyplot(fig4, use_container_width=True)
        else:
            st.write("Need at least 2 Method A responses to plot this.")

    with col4:
        if len(df_dc) > 1 and df_dc["dc_vote"].nunique() > 1:
            fig5, ax5 = plt.subplots(figsize=(9, 6))
            sns.boxplot(data=df_dc, x="dc_vote", y="env_score", order=["No", "Yes"],
                       palette=[SECONDARY_COLOR, PRIMARY_COLOR], ax=ax5)
            ax5.set_xlabel('Vote', fontweight='bold')
            ax5.set_ylabel('Environmental Attitude Index (1-5)', fontweight='bold')
            style_axes(ax5)
            fig5.tight_layout()
            st.pyplot(fig5, use_container_width=True)
        else:
            st.write("Need Yes and No votes in Method B to plot this.")

    st.divider()

    # --- Reset (guarded) ---
    st.subheader("Presenter Controls")
    confirm_reset = st.checkbox("I understand this will permanently delete all collected responses.")
    if st.button("🗑️ Reset Data (Start Fresh)", disabled=not confirm_reset):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        st.rerun()
