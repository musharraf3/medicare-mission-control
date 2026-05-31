import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import json

# =============================================================================
# APP CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="Medicare Mission Control",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CUSTOM CSS
# =============================================================================
st.markdown("""
<style>
    .mission-hero {
        background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
        padding: 2.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .mission-hero h1 {
        color: white !important;
        font-size: 2.2rem;
        margin-bottom: 0.3rem;
    }
    .mission-hero p {
        color: #e3f2fd;
        font-size: 1.1rem;
        margin: 0;
    }
    .mission-card {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-left: 4px solid #1565c0;
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .mission-card h4 {
        color: #1565c0;
        margin: 0 0 0.5rem 0;
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .mission-card .county-name {
        font-size: 1.3rem;
        font-weight: 700;
        color: #212121;
        margin-bottom: 0.3rem;
    }
    .mission-card .score-badge {
        display: inline-block;
        background: #e3f2fd;
        color: #1565c0;
        padding: 2px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .mission-card .detail {
        color: #616161;
        font-size: 0.9rem;
        margin: 0.3rem 0;
    }
    .mission-card .action {
        color: #2e7d32;
        font-weight: 500;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    .advisor-card {
        background: #fafafa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.2rem;
        height: 100%;
    }
    .advisor-card h4 {
        color: #37474f;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        margin-bottom: 0.8rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #1565c0;
    }
    .advisor-card p {
        color: #424242;
        font-size: 0.88rem;
        line-height: 1.5;
    }
    .creativity-badge {
        display: none;
    }
    .battle-card {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }
    .battle-card h3 {
        color: #1a237e;
        border-bottom: 2px solid #1565c0;
        padding-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# PATHS
# =============================================================================
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
MEDICARE_FILE = os.path.join(DATA_DIR, "Medicare Monthly Enrollment Data_January 2026.csv")
PLACES_FILE = os.path.join(DATA_DIR, "PLACES__Local_Data_for_Better_Health,_County_Data,_2025_release_20260515.csv")

# =============================================================================
# CONSTANTS
# =============================================================================
MEDICARE_FIELDS = [
    "TOT_BENES", "MA_AND_OTH_BENES", "ORGNL_MDCR_BENES", "DUAL_TOT_BENES",
    "FULL_DUAL_TOT_BENES", "PART_DUAL_TOT_BENES", "PRSCRPTN_DRUG_TOT_BENES",
    "PRSCRPTN_DRUG_MAPD_BENES", "PRSCRPTN_DRUG_PDP_BENES",
    "PRSCRPTN_DRUG_DEEMED_ELIGIBLE_FULL_LIS_BENES", "PRSCRPTN_DRUG_FULL_LIS_BENES",
    "PRSCRPTN_DRUG_PARTIAL_LIS_BENES", "PRSCRPTN_DRUG_NO_LIS_BENES",
    "AGE_75_TO_79_BENES", "AGE_80_TO_84_BENES", "AGE_85_TO_89_BENES",
    "AGE_90_TO_94_BENES", "AGE_GT_94_BENES",
]

PLACES_MEASURES = [
    "DIABETES", "BPHIGH", "CHD", "COPD", "STROKE", "OBESITY",
    "CSMOKING", "LPA", "DEPRESSION", "FOODINSECU", "LACKTRPT", "MOBILITY",
]

CHRONIC_MEASURES = ["DIABETES", "BPHIGH", "CHD", "COPD", "STROKE", "OBESITY", "CSMOKING", "LPA", "DEPRESSION"]
SOCIAL_MEASURES = ["FOODINSECU", "LACKTRPT", "MOBILITY"]

MEASURE_LABELS = {
    "DIABETES": "Diabetes", "BPHIGH": "High Blood Pressure", "CHD": "Coronary Heart Disease",
    "COPD": "COPD", "STROKE": "Stroke", "OBESITY": "Obesity", "CSMOKING": "Current Smoking",
    "LPA": "Physical Inactivity", "DEPRESSION": "Depression", "FOODINSECU": "Food Insecurity",
    "LACKTRPT": "Lack of Transportation", "MOBILITY": "Mobility Disability",
}


# =============================================================================
# DATA LOADING
# =============================================================================
@st.cache_data(show_spinner="Loading Medicare enrollment data...")
def load_medicare():
    if not os.path.exists(MEDICARE_FILE):
        st.error(f"Medicare file not found: {MEDICARE_FILE}")
        return pd.DataFrame()
    df = pd.read_csv(MEDICARE_FILE, dtype=str, low_memory=False)
    df.columns = df.columns.str.strip().str.upper()
    # Filter to 2026, January, County level
    df = df[(df["YEAR"] == "2026") & (df["MONTH"] == "January") & (df["BENE_GEO_LVL"] == "County")].copy()
    # FIPS normalization
    df["FIPS"] = df["BENE_FIPS_CD"].str.strip().str.zfill(5)
    # Replace suppressed values and convert numeric fields
    for col in MEDICARE_FIELDS:
        if col in df.columns:
            df[col] = df[col].replace("*", np.nan)
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Keep useful identifier columns
    df["STATE"] = df["BENE_STATE_ABRVTN"].str.strip()
    df["COUNTY"] = df["BENE_COUNTY_DESC"].str.strip()
    return df[["FIPS", "STATE", "COUNTY"] + [c for c in MEDICARE_FIELDS if c in df.columns]].reset_index(drop=True)


@st.cache_data(show_spinner="Loading CDC PLACES health data...")
def load_places():
    if not os.path.exists(PLACES_FILE):
        st.error(f"PLACES file not found: {PLACES_FILE}")
        return pd.DataFrame()
    df = pd.read_csv(PLACES_FILE, dtype=str, low_memory=False)
    df.columns = df.columns.str.strip()
    # Normalize column names for filtering
    col_map = {c: c.upper() for c in df.columns}
    df.rename(columns=col_map, inplace=True)
    # Filter
    df = df[(df["YEAR"] == "2023") & (df["DATA_VALUE_TYPE"] == "Age-adjusted prevalence")].copy()
    df = df[df["MEASUREID"].isin(PLACES_MEASURES)]
    # FIPS normalization
    df["FIPS"] = df["LOCATIONID"].str.strip().str.zfill(5)
    df["DATA_VALUE"] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")
    # Pivot: each measure becomes a column
    pivot = df.pivot_table(index="FIPS", columns="MEASUREID", values="DATA_VALUE", aggfunc="first").reset_index()
    pivot.columns.name = None
    return pivot


@st.cache_data(show_spinner="Building analytics dataset...")
def build_dataset():
    medicare = load_medicare()
    places = load_places()
    if medicare.empty or places.empty:
        return pd.DataFrame()
    # Merge
    merged = medicare.merge(places, on="FIPS", how="inner")
    # Derived metrics
    merged["MA_PENETRATION"] = merged["MA_AND_OTH_BENES"] / merged["TOT_BENES"]
    merged["ORIG_MEDICARE_RATE"] = merged["ORGNL_MDCR_BENES"] / merged["TOT_BENES"]
    merged["DUAL_ELIGIBLE_RATE"] = merged["DUAL_TOT_BENES"] / merged["TOT_BENES"]
    merged["PART_D_PENETRATION"] = merged["PRSCRPTN_DRUG_TOT_BENES"] / merged["TOT_BENES"]

    lis_numerator = (
        merged["PRSCRPTN_DRUG_DEEMED_ELIGIBLE_FULL_LIS_BENES"].fillna(0)
        + merged["PRSCRPTN_DRUG_FULL_LIS_BENES"].fillna(0)
        + merged["PRSCRPTN_DRUG_PARTIAL_LIS_BENES"].fillna(0)
    )
    merged["LIS_RATE"] = lis_numerator / merged["PRSCRPTN_DRUG_TOT_BENES"]

    age75_cols = ["AGE_75_TO_79_BENES", "AGE_80_TO_84_BENES", "AGE_85_TO_89_BENES", "AGE_90_TO_94_BENES", "AGE_GT_94_BENES"]
    merged["AGE_75_PLUS_RATE"] = merged[age75_cols].sum(axis=1) / merged["TOT_BENES"]

    # Percentile ranks for chronic measures
    for m in CHRONIC_MEASURES:
        if m in merged.columns:
            merged[f"{m}_PCTILE"] = merged[m].rank(pct=True)
    chronic_pctile_cols = [f"{m}_PCTILE" for m in CHRONIC_MEASURES if f"{m}_PCTILE" in merged.columns]
    merged["CHRONIC_BURDEN_INDEX"] = merged[chronic_pctile_cols].mean(axis=1)

    # Social need index
    for m in SOCIAL_MEASURES:
        if m in merged.columns:
            merged[f"{m}_PCTILE"] = merged[m].rank(pct=True)
    social_pctile_cols = [f"{m}_PCTILE" for m in SOCIAL_MEASURES if f"{m}_PCTILE" in merged.columns]
    merged["SOCIAL_NEED_INDEX"] = merged[social_pctile_cols].mean(axis=1)

    # Medicare opportunity index
    merged["MEDICARE_OPP_INDEX"] = merged["TOT_BENES"].rank(pct=True)

    # Dual eligible rate percentile and LIS rate percentile
    merged["DUAL_RATE_PCTILE"] = merged["DUAL_ELIGIBLE_RATE"].rank(pct=True)
    merged["LIS_RATE_PCTILE"] = merged["LIS_RATE"].rank(pct=True)

    # Outreach priority score
    merged["OUTREACH_PRIORITY_RAW"] = (
        0.30 * merged["MEDICARE_OPP_INDEX"]
        + 0.25 * merged["CHRONIC_BURDEN_INDEX"]
        + 0.20 * merged["DUAL_RATE_PCTILE"]
        + 0.15 * merged["SOCIAL_NEED_INDEX"]
        + 0.10 * merged["LIS_RATE_PCTILE"]
    )
    # Normalize 0-100
    raw_min = merged["OUTREACH_PRIORITY_RAW"].min()
    raw_max = merged["OUTREACH_PRIORITY_RAW"].max()
    if raw_max > raw_min:
        merged["OUTREACH_PRIORITY_SCORE"] = ((merged["OUTREACH_PRIORITY_RAW"] - raw_min) / (raw_max - raw_min)) * 100
    else:
        merged["OUTREACH_PRIORITY_SCORE"] = 50.0

    return merged.sort_values("OUTREACH_PRIORITY_SCORE", ascending=False).reset_index(drop=True)


# =============================================================================
# HEADER
# =============================================================================
def render_header():
    st.markdown("# Medicare Access & Chronic Risk Copilot")
    st.markdown(
        "**AI-powered county prioritization for Medicare outreach, chronic care, and access planning.**"
    )


# =============================================================================
# SIDEBAR
# =============================================================================
def render_sidebar(df):
    st.sidebar.title("Medicare Access & Chronic Risk Copilot")
    st.sidebar.markdown("---")
    st.sidebar.subheader("State Presets")
    demo_state = st.sidebar.radio(
        "Quick filter:",
        ["All States", "California", "Texas", "Florida", "New York"],
        index=0,
    )
    state_abbr_map = {"California": "CA", "Texas": "TX", "Florida": "FL", "New York": "NY"}
    if demo_state != "All States":
        df = df[df["STATE"] == state_abbr_map[demo_state]]

    st.sidebar.markdown("---")
    st.sidebar.subheader("Filters")
    states = sorted(df["STATE"].dropna().unique())
    selected_states = st.sidebar.multiselect("States", states, default=[])
    if selected_states:
        df = df[df["STATE"].isin(selected_states)]

    min_benes = st.sidebar.number_input("Min Medicare Beneficiaries", min_value=0, value=0, step=1000)
    if min_benes > 0:
        df = df[df["TOT_BENES"] >= min_benes]

    dual_range = st.sidebar.slider("Dual Eligible Rate Range", 0.0, 1.0, (0.0, 1.0), 0.01)
    df = df[(df["DUAL_ELIGIBLE_RATE"] >= dual_range[0]) & (df["DUAL_ELIGIBLE_RATE"] <= dual_range[1])]

    ma_range = st.sidebar.slider("MA Penetration Range", 0.0, 1.0, (0.0, 1.0), 0.01)
    df = df[(df["MA_PENETRATION"] >= ma_range[0]) & (df["MA_PENETRATION"] <= ma_range[1])]

    chronic_level = st.sidebar.slider("Min Chronic Burden Index", 0.0, 1.0, 0.0, 0.01)
    df = df[df["CHRONIC_BURDEN_INDEX"] >= chronic_level]

    st.sidebar.markdown("---")
    st.sidebar.caption("Data: CMS Medicare Monthly Enrollment (Jan 2026) + CDC PLACES (2023)")

    return df


# =============================================================================
# TAB 0: MISSION CONTROL
# =============================================================================
def render_mission_control(df):
    # Hero banner
    st.markdown("""
    <div class="mission-hero">
        <h1>Medicare Mission Control</h1>
        <p>Find the counties where outreach can create the highest impact.</p>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.warning("No data available for the current filters.")
        return

    # --- Three Mission Cards ---
    st.markdown("### Priority Missions")
    mc1, mc2, mc3 = st.columns(3)

    # Card 1: Highest Outreach Priority
    top_outreach = df.iloc[0]
    with mc1:
        drivers_1 = []
        if pd.notna(top_outreach.get("CHRONIC_BURDEN_INDEX")) and top_outreach["CHRONIC_BURDEN_INDEX"] > 0.7:
            drivers_1.append("elevated chronic burden")
        if pd.notna(top_outreach.get("DUAL_ELIGIBLE_RATE")) and top_outreach["DUAL_ELIGIBLE_RATE"] > 0.2:
            drivers_1.append(f"dual rate {top_outreach['DUAL_ELIGIBLE_RATE']:.0%}")
        if pd.notna(top_outreach.get("TOT_BENES")) and top_outreach["TOT_BENES"] > 50000:
            drivers_1.append("large Medicare population")
        driver_text_1 = "; ".join(drivers_1) if drivers_1 else "high composite risk"
        st.markdown(f"""
        <div class="mission-card">
            <h4>Highest Outreach Priority</h4>
            <div class="county-name">{top_outreach['COUNTY']}, {top_outreach['STATE']}</div>
            <span class="score-badge">Score: {top_outreach['OUTREACH_PRIORITY_SCORE']:.1f}/100</span>
            <p class="detail">Key driver: {driver_text_1}</p>
            <p class="action">Action: Deploy field marketing and broker activation immediately.</p>
        </div>
        """, unsafe_allow_html=True)

    # Card 2: Highest Dual-Eligible Opportunity
    top_dual = df.nlargest(1, "DUAL_ELIGIBLE_RATE").iloc[0]
    with mc2:
        st.markdown(f"""
        <div class="mission-card">
            <h4>Highest Dual-Eligible Opportunity</h4>
            <div class="county-name">{top_dual['COUNTY']}, {top_dual['STATE']}</div>
            <span class="score-badge">Dual Rate: {top_dual['DUAL_ELIGIBLE_RATE']:.0%}</span>
            <p class="detail">Key driver: {top_dual['TOT_BENES']:,.0f} beneficiaries with D-SNP potential</p>
            <p class="action">Action: Launch D-SNP enrollment campaign and Medicaid MCO coordination.</p>
        </div>
        """, unsafe_allow_html=True)

    # Card 3: Highest Chronic Burden Hotspot
    top_chronic = df.nlargest(1, "CHRONIC_BURDEN_INDEX").iloc[0]
    with mc3:
        chronic_drivers = []
        if pd.notna(top_chronic.get("DIABETES")) and top_chronic["DIABETES"] > 14:
            chronic_drivers.append(f"diabetes {top_chronic['DIABETES']:.1f}%")
        if pd.notna(top_chronic.get("COPD")) and top_chronic["COPD"] > 8:
            chronic_drivers.append(f"COPD {top_chronic['COPD']:.1f}%")
        if pd.notna(top_chronic.get("BPHIGH")) and top_chronic["BPHIGH"] > 35:
            chronic_drivers.append(f"hypertension {top_chronic['BPHIGH']:.1f}%")
        chronic_driver_text = "; ".join(chronic_drivers) if chronic_drivers else "multi-condition burden"
        st.markdown(f"""
        <div class="mission-card">
            <h4>Highest Chronic Burden Hotspot</h4>
            <div class="county-name">{top_chronic['COUNTY']}, {top_chronic['STATE']}</div>
            <span class="score-badge">Burden Index: {top_chronic['CHRONIC_BURDEN_INDEX']:.2f}</span>
            <p class="detail">Key driver: {chronic_driver_text}</p>
            <p class="action">Action: Deploy value-based care models and remote monitoring programs.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- Intervention Simulator ---
    st.markdown("### Intervention Simulator")
    st.caption("Model outreach capacity and see how many priority counties your budget can cover.")

    sim_col1, sim_col2 = st.columns([1, 2])

    with sim_col1:
        budget = st.slider("Outreach Budget ($)", 50000, 5000000, 500000, 50000)
        cost_per = st.slider("Cost per Outreach ($)", 5, 100, 25, 5)
        engagement_pct = st.slider("Expected Engagement Rate (%)", 5, 40, 15, 1)
        conversion_pct = st.slider("Care-Mgmt Conversion Rate (%)", 5, 50, 20, 1)

    engagement_rate = engagement_pct / 100.0
    conversion_rate = conversion_pct / 100.0

    total_reachable = int(budget / cost_per)
    total_engaged = int(total_reachable * engagement_rate)
    total_converted = int(total_engaged * conversion_rate)

    with sim_col2:
        s1, s2, s3 = st.columns(3)
        s1.metric("Beneficiaries Reachable", f"{total_reachable:,}")
        s2.metric("Estimated Engaged", f"{total_engaged:,}")
        s3.metric("Care-Mgmt Enrollments", f"{total_converted:,}")

        # Allocate across top counties
        alloc_df = df.head(20).copy()
        alloc_df["WEIGHT"] = alloc_df["OUTREACH_PRIORITY_SCORE"] * alloc_df["TOT_BENES"]
        weight_sum = alloc_df["WEIGHT"].sum()
        if weight_sum > 0:
            alloc_df["ALLOC_SHARE"] = alloc_df["WEIGHT"] / weight_sum
        else:
            alloc_df["ALLOC_SHARE"] = 1 / len(alloc_df)
        alloc_df["ALLOCATED_OUTREACH"] = (alloc_df["ALLOC_SHARE"] * total_reachable).astype(int)
        alloc_df["EST_ENGAGED"] = (alloc_df["ALLOCATED_OUTREACH"] * engagement_rate).astype(int)

        # How many counties can be meaningfully covered (at least 100 outreach each)
        covered = (alloc_df["ALLOCATED_OUTREACH"] >= 100).sum()
        st.metric("Counties Covered (100+ outreach)", f"{covered}")

    # Allocation table
    st.markdown("**Recommended County Allocation**")
    alloc_display = alloc_df[["STATE", "COUNTY", "OUTREACH_PRIORITY_SCORE", "TOT_BENES", "ALLOCATED_OUTREACH", "EST_ENGAGED"]].copy()
    alloc_display.columns = ["State", "County", "Priority Score", "Medicare Pop.", "Allocated Outreach", "Est. Engaged"]
    alloc_display["Priority Score"] = alloc_display["Priority Score"].apply(lambda x: f"{x:.1f}")
    alloc_display["Medicare Pop."] = alloc_display["Medicare Pop."].apply(lambda x: f"{x:,.0f}")
    st.dataframe(alloc_display.head(10), use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- County Battle Card ---
    st.markdown("### County Battle Card")
    st.caption("Select a county to generate a one-page outreach profile and 90-day action plan.")

    county_options = (df["COUNTY"] + ", " + df["STATE"]).tolist()
    selected_county_label = st.selectbox("Select a county:", county_options[:200], index=0)

    if selected_county_label:
        parts = selected_county_label.rsplit(", ", 1)
        county_name = parts[0]
        state_abbr = parts[1] if len(parts) > 1 else ""
        county_row = df[(df["COUNTY"] == county_name) & (df["STATE"] == state_abbr)]
        if not county_row.empty:
            r = county_row.iloc[0]
            st.markdown(f"### {r['COUNTY']}, {r['STATE']}")

            bc1, bc2, bc3, bc4 = st.columns(4)
            bc1.metric("Medicare Pop.", f"{r['TOT_BENES']:,.0f}")
            bc2.metric("MA Penetration", f"{r['MA_PENETRATION']:.1%}" if pd.notna(r.get("MA_PENETRATION")) else "N/A")
            bc3.metric("Dual Eligible Rate", f"{r['DUAL_ELIGIBLE_RATE']:.1%}" if pd.notna(r.get("DUAL_ELIGIBLE_RATE")) else "N/A")
            bc4.metric("Priority Score", f"{r['OUTREACH_PRIORITY_SCORE']:.1f}/100")

            bc5, bc6, bc7, bc8 = st.columns(4)
            bc5.metric("LIS Rate", f"{r['LIS_RATE']:.1%}" if pd.notna(r.get("LIS_RATE")) else "N/A")
            bc6.metric("Age 75+ Rate", f"{r['AGE_75_PLUS_RATE']:.1%}" if pd.notna(r.get("AGE_75_PLUS_RATE")) else "N/A")
            bc7.metric("Chronic Burden", f"{r['CHRONIC_BURDEN_INDEX']:.2f}" if pd.notna(r.get("CHRONIC_BURDEN_INDEX")) else "N/A")
            bc8.metric("Social Need", f"{r['SOCIAL_NEED_INDEX']:.2f}" if pd.notna(r.get("SOCIAL_NEED_INDEX")) else "N/A")

            # Top 3 risk drivers
            st.markdown("**Top Risk Drivers:**")
            risk_items = []
            if pd.notna(r.get("DIABETES")) and r["DIABETES"] > 10:
                risk_items.append(f"Diabetes prevalence: {r['DIABETES']:.1f}%")
            if pd.notna(r.get("BPHIGH")) and r["BPHIGH"] > 30:
                risk_items.append(f"High blood pressure: {r['BPHIGH']:.1f}%")
            if pd.notna(r.get("COPD")) and r["COPD"] > 6:
                risk_items.append(f"COPD: {r['COPD']:.1f}%")
            if pd.notna(r.get("OBESITY")) and r["OBESITY"] > 30:
                risk_items.append(f"Obesity: {r['OBESITY']:.1f}%")
            if pd.notna(r.get("FOODINSECU")) and r["FOODINSECU"] > 15:
                risk_items.append(f"Food insecurity: {r['FOODINSECU']:.1f}%")
            if pd.notna(r.get("DUAL_ELIGIBLE_RATE")) and r["DUAL_ELIGIBLE_RATE"] > 0.25:
                risk_items.append(f"High dual-eligible rate: {r['DUAL_ELIGIBLE_RATE']:.0%}")
            for item in risk_items[:3]:
                st.markdown(f"- {item}")
            if not risk_items:
                st.markdown("- Combined multi-factor risk above national median")

            # 90-day action plan
            st.markdown("**90-Day Action Plan:**")
            st.markdown(f"""
| Phase | Timeline | Actions |
|-------|----------|---------|
| **Identify & Segment** | Days 1-30 | Pull beneficiary lists for {r['COUNTY']}. Segment by dual status, LIS eligibility, and chronic conditions. Identify high-risk members for care management. |
| **Launch Outreach** | Days 31-60 | Deploy direct mail and telephonic campaigns. Activate local brokers. Partner with community health organizations and county health departments. |
| **Measure & Refine** | Days 61-90 | Track engagement rates, enrollment conversions, and care-management uptake. Refine messaging and channel mix based on response data. Report ROI to leadership. |
""")

    st.markdown("---")

    # --- AI Strategy Council ---
    st.markdown("### AI Strategy Council")
    st.caption("Four advisory perspectives on the current filtered data.")

    adv1, adv2, adv3, adv4 = st.columns(4)

    avg_ma = df["MA_PENETRATION"].mean()
    avg_dual = df["DUAL_ELIGIBLE_RATE"].mean()
    avg_chronic = df["CHRONIC_BURDEN_INDEX"].mean()
    top_county = df.iloc[0]["COUNTY"] + ", " + df.iloc[0]["STATE"]
    total_benes = df["TOT_BENES"].sum()
    high_social = (df["SOCIAL_NEED_INDEX"] > 0.7).sum()

    with adv1:
        if avg_ma < 0.5:
            growth_rec = f"MA penetration averages {avg_ma:.0%} in this view. Significant growth headroom exists. Prioritize network adequacy filings and broker incentive programs in the top 5 counties."
        else:
            growth_rec = f"MA penetration is already {avg_ma:.0%}. Focus on retention and Star Ratings improvement rather than new enrollment acquisition."
        st.markdown(f"""
        <div class="advisor-card">
            <h4>Market Growth Advisor</h4>
            <p>{growth_rec}</p>
        </div>
        """, unsafe_allow_html=True)

    with adv2:
        high_chronic_n = (df["CHRONIC_BURDEN_INDEX"] > 0.75).sum()
        care_rec = f"{high_chronic_n} counties exceed the 75th percentile for chronic burden. Deploy condition-specific care management (diabetes, COPD, CHD) and remote patient monitoring in {top_county} first."
        st.markdown(f"""
        <div class="advisor-card">
            <h4>Care Management Advisor</h4>
            <p>{care_rec}</p>
        </div>
        """, unsafe_allow_html=True)

    with adv3:
        equity_rec = f"{high_social} counties show elevated social need (food insecurity, transportation, mobility). Dual-eligible rate averages {avg_dual:.0%}. Invest in supplemental benefits, community health worker programs, and SDOH screening at {top_county}."
        st.markdown(f"""
        <div class="advisor-card">
            <h4>Health Equity Advisor</h4>
            <p>{equity_rec}</p>
        </div>
        """, unsafe_allow_html=True)

    with adv4:
        exec_rec = f"This geography covers {total_benes:,.0f} Medicare beneficiaries across {len(df):,} counties. Recommended board-level message: invest in the top 10 priority counties for maximum outreach ROI before AEP, with D-SNP expansion in high-dual markets."
        st.markdown(f"""
        <div class="advisor-card">
            <h4>Executive Strategy Advisor</h4>
            <p>{exec_rec}</p>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# TAB 1: EXECUTIVE OVERVIEW
# =============================================================================
def render_executive_overview(df, full_df):
    st.markdown("## Executive Overview")
    st.markdown(
        "> This view summarizes the national Medicare landscape and highlights counties "
        "with the highest outreach priority based on enrollment size, chronic burden, and social need."
    )

    st.markdown("---")

    # KPI Cards
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    total_benes = full_df["TOT_BENES"].sum()
    total_counties = full_df["FIPS"].nunique()
    avg_ma = full_df["MA_PENETRATION"].mean()
    avg_dual = full_df["DUAL_ELIGIBLE_RATE"].mean()
    top_state = full_df.groupby("STATE")["OUTREACH_PRIORITY_SCORE"].mean().idxmax() if not full_df.empty else "N/A"
    high_priority_count = (full_df["OUTREACH_PRIORITY_SCORE"] >= 75).sum()

    col1.metric("Total Beneficiaries", f"{total_benes:,.0f}")
    col2.metric("Counties Analyzed", f"{total_counties:,}")
    col3.metric("Avg MA Penetration", f"{avg_ma:.1%}")
    col4.metric("Avg Dual Rate", f"{avg_dual:.1%}")
    col5.metric("Top Priority State", top_state)
    col6.metric("High-Priority Counties", f"{high_priority_count:,}")

    st.markdown("---")

    # Charts row
    chart_col1, chart_col2 = st.columns([3, 2])

    with chart_col1:
        st.markdown("#### U.S. County Outreach Priority")
        try:
            map_df = df.head(500).copy()
            # Use state-level aggregation for cleaner map
            state_agg = df.groupby("STATE").agg(
                avg_score=("OUTREACH_PRIORITY_SCORE", "mean"),
                total_benes=("TOT_BENES", "sum"),
                counties=("FIPS", "nunique"),
            ).reset_index()
            fig_map = px.choropleth(
                state_agg,
                locations="STATE",
                locationmode="USA-states",
                color="avg_score",
                color_continuous_scale="Reds",
                scope="usa",
                hover_data={"total_benes": ":,.0f", "counties": True},
                labels={"avg_score": "Avg Priority Score", "STATE": "State", "total_benes": "Total Beneficiaries"},
            )
            fig_map.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=400)
            st.plotly_chart(fig_map, use_container_width=True)
        except Exception:
            st.info("Map visualization unavailable. Showing state summary instead.")
            state_agg = df.groupby("STATE")["OUTREACH_PRIORITY_SCORE"].mean().sort_values(ascending=False).head(15)
            fig_bar = px.bar(
                x=state_agg.index, y=state_agg.values,
                labels={"x": "State", "y": "Avg Outreach Priority Score"},
                color=state_agg.values, color_continuous_scale="Reds",
            )
            fig_bar.update_layout(height=400)
            st.plotly_chart(fig_bar, use_container_width=True)

    with chart_col2:
        st.markdown("#### Top 10 Priority Counties")
        try:
            top10 = df.head(10)[["STATE", "COUNTY", "OUTREACH_PRIORITY_SCORE"]].copy()
            top10["Label"] = top10["COUNTY"] + ", " + top10["STATE"]
            fig_top = px.bar(
                top10, x="OUTREACH_PRIORITY_SCORE", y="Label", orientation="h",
                color="OUTREACH_PRIORITY_SCORE", color_continuous_scale="Reds",
                labels={"OUTREACH_PRIORITY_SCORE": "Priority Score", "Label": ""},
            )
            fig_top.update_layout(height=400, showlegend=False, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_top, use_container_width=True)
        except Exception:
            st.info("Chart unavailable. Top counties listed below.")
            st.dataframe(df.head(10)[["STATE", "COUNTY", "OUTREACH_PRIORITY_SCORE"]])


# =============================================================================
# TAB 2: COUNTY PRIORITIZATION
# =============================================================================
def render_county_prioritization(df):
    st.markdown("## County Prioritization")
    st.markdown("Ranked list of counties by Outreach Priority Score. Use sidebar filters to narrow results.")

    display_cols = {
        "STATE": "State", "COUNTY": "County", "FIPS": "FIPS",
        "TOT_BENES": "Total Beneficiaries", "MA_PENETRATION": "MA Penetration",
        "DUAL_ELIGIBLE_RATE": "Dual Eligible Rate", "LIS_RATE": "LIS Rate",
        "AGE_75_PLUS_RATE": "Age 75+ Rate",
    }
    # Add available PLACES measures
    for m in ["DIABETES", "BPHIGH", "COPD", "CHD", "STROKE", "FOODINSECU", "LACKTRPT"]:
        if m in df.columns:
            display_cols[m] = MEASURE_LABELS.get(m, m)
    display_cols["OUTREACH_PRIORITY_SCORE"] = "Outreach Priority Score"

    available_cols = [c for c in display_cols.keys() if c in df.columns]
    table_df = df[available_cols].copy()
    table_df.rename(columns={c: display_cols[c] for c in available_cols}, inplace=True)

    # Format
    pct_cols = ["MA Penetration", "Dual Eligible Rate", "LIS Rate", "Age 75+ Rate"]
    for pc in pct_cols:
        if pc in table_df.columns:
            table_df[pc] = table_df[pc].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "—")

    if "Total Beneficiaries" in table_df.columns:
        table_df["Total Beneficiaries"] = table_df["Total Beneficiaries"].apply(
            lambda x: f"{x:,.0f}" if pd.notna(x) else "—"
        )

    if "Outreach Priority Score" in table_df.columns:
        table_df["Outreach Priority Score"] = table_df["Outreach Priority Score"].apply(
            lambda x: f"{x:.1f}" if pd.notna(x) else "—"
        )

    # Prevalence formatting
    for m in ["DIABETES", "BPHIGH", "COPD", "CHD", "STROKE", "FOODINSECU", "LACKTRPT"]:
        label = MEASURE_LABELS.get(m, m)
        if label in table_df.columns:
            table_df[label] = table_df[label].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")

    st.dataframe(table_df.head(200), use_container_width=True, height=500)

    # Download
    csv_data = df[available_cols].to_csv(index=False)
    st.download_button("Download Filtered Data (CSV)", csv_data, "county_prioritization.csv", "text/csv")

    # Summary
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Counties Shown", f"{len(df):,}")
    c2.metric("Avg Priority Score", f"{df['OUTREACH_PRIORITY_SCORE'].mean():.1f}")
    c3.metric("Total Beneficiaries", f"{df['TOT_BENES'].sum():,.0f}")


# =============================================================================
# TAB 3: CHRONIC RISK EXPLORER
# =============================================================================
def render_chronic_explorer(df):
    st.markdown("## Chronic Risk Explorer")

    # Measure selector
    available_measures = [m for m in PLACES_MEASURES if m in df.columns]
    selected_measure = st.selectbox(
        "Select a health measure to explore:",
        available_measures,
        format_func=lambda x: MEASURE_LABELS.get(x, x),
    )

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("#### Diabetes vs. Dual Eligible Rate")
        try:
            scatter_df = df.dropna(subset=["DIABETES", "DUAL_ELIGIBLE_RATE", "TOT_BENES"]).copy()
            if not scatter_df.empty:
                fig_scatter = px.scatter(
                    scatter_df.head(1000),
                    x="DIABETES", y="DUAL_ELIGIBLE_RATE",
                    size="TOT_BENES", color="OUTREACH_PRIORITY_SCORE",
                    color_continuous_scale="Reds",
                    hover_data=["STATE", "COUNTY"],
                    labels={"DIABETES": "Diabetes Prevalence (%)", "DUAL_ELIGIBLE_RATE": "Dual Eligible Rate",
                             "TOT_BENES": "Medicare Beneficiaries", "OUTREACH_PRIORITY_SCORE": "Priority Score"},
                    size_max=40,
                )
                fig_scatter.update_layout(height=420)
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("Insufficient data for scatter plot.")
        except Exception:
            st.info("Scatter plot unavailable for this selection.")

    with chart_col2:
        st.markdown(f"#### Top 20 Counties: {MEASURE_LABELS.get(selected_measure, selected_measure)}")
        try:
            if selected_measure in df.columns:
                top_measure = df.dropna(subset=[selected_measure]).nlargest(20, selected_measure)
                top_measure["Label"] = top_measure["COUNTY"] + ", " + top_measure["STATE"]
                fig_top_m = px.bar(
                    top_measure, x=selected_measure, y="Label", orientation="h",
                    color=selected_measure, color_continuous_scale="Oranges",
                    labels={selected_measure: f"{MEASURE_LABELS.get(selected_measure, selected_measure)} (%)", "Label": ""},
                )
                fig_top_m.update_layout(height=420, yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_top_m, use_container_width=True)
        except Exception:
            st.info("Bar chart unavailable for this measure.")

    st.markdown("---")

    # Chronic burden by state
    st.markdown("#### Average Chronic Burden Index by State")
    try:
        state_burden = df.groupby("STATE")["CHRONIC_BURDEN_INDEX"].mean().sort_values(ascending=False).head(20).reset_index()
        fig_state = px.bar(
            state_burden, x="STATE", y="CHRONIC_BURDEN_INDEX",
            color="CHRONIC_BURDEN_INDEX", color_continuous_scale="YlOrRd",
            labels={"STATE": "State", "CHRONIC_BURDEN_INDEX": "Chronic Burden Index"},
        )
        fig_state.update_layout(height=350)
        st.plotly_chart(fig_state, use_container_width=True)
    except Exception:
        st.info("State burden chart unavailable.")

    # Correlation heatmap
    st.markdown("#### Correlation: Health Measures vs. Medicare Metrics")
    try:
        corr_cols = [m for m in PLACES_MEASURES if m in df.columns]
        metric_cols = ["MA_PENETRATION", "DUAL_ELIGIBLE_RATE", "LIS_RATE", "AGE_75_PLUS_RATE", "OUTREACH_PRIORITY_SCORE"]
        metric_cols = [c for c in metric_cols if c in df.columns]
        if corr_cols and metric_cols:
            corr_matrix = df[corr_cols + metric_cols].corr().loc[corr_cols, metric_cols]
            fig_heatmap = px.imshow(
                corr_matrix,
                x=[c.replace("_", " ").title() for c in metric_cols],
                y=[MEASURE_LABELS.get(m, m) for m in corr_cols],
                color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                labels={"color": "Correlation"},
            )
            fig_heatmap.update_layout(height=450)
            st.plotly_chart(fig_heatmap, use_container_width=True)
    except Exception:
        st.info("Correlation heatmap unavailable.")


# =============================================================================
# TAB 4: AI ACTION SUMMARY
# =============================================================================
def render_ai_summary(df):
    st.markdown("## AI Action Summary")
    st.markdown("Strategic recommendations generated from the current filtered dataset.")

    if df.empty:
        st.warning("No data available for the current filters.")
        return

    # Top 3 priority counties
    top3 = df.head(3)

    st.markdown("### Priority Geographies")
    for rank, (i, row) in enumerate(top3.iterrows(), start=1):
        score = row["OUTREACH_PRIORITY_SCORE"]
        county = row["COUNTY"]
        state = row["STATE"]
        benes = row["TOT_BENES"]
        dual = row["DUAL_ELIGIBLE_RATE"]
        chronic = row["CHRONIC_BURDEN_INDEX"]
        diabetes = row.get("DIABETES", np.nan)

        # Determine risk drivers
        drivers = []
        if pd.notna(dual) and dual > 0.3:
            drivers.append(f"high dual-eligible concentration ({dual:.0%})")
        if pd.notna(chronic) and chronic > 0.7:
            drivers.append(f"elevated chronic burden (index {chronic:.2f})")
        if pd.notna(diabetes) and diabetes > 15:
            drivers.append(f"diabetes prevalence ({diabetes:.1f}%)")
        if pd.notna(benes) and benes > 50000:
            drivers.append(f"large Medicare population ({benes:,.0f})")
        if not drivers:
            drivers.append("combined risk factor concentration")

        st.markdown(f"""
**{rank}. {county}, {state}** — Priority Score: **{score:.1f} / 100**
- Medicare Beneficiaries: {benes:,.0f}
- Dual Eligible Rate: {dual:.1%}
- Risk Drivers: {'; '.join(drivers)}
""")

    st.markdown("---")
    st.markdown("### Recommended Payer Actions")

    # Generate deterministic recommendations
    avg_ma = df["MA_PENETRATION"].mean()
    avg_dual = df["DUAL_ELIGIBLE_RATE"].mean()
    high_chronic_counties = (df["CHRONIC_BURDEN_INDEX"] > 0.75).sum()

    recommendations = []
    if avg_ma < 0.5:
        recommendations.append("**Network Expansion**: Average MA penetration is below 50% in the filtered geography. Consider expanding MA plan availability and broker partnerships in underserved counties.")
    if avg_dual > 0.2:
        recommendations.append("**D-SNP Opportunity**: Dual-eligible rate exceeds 20% on average. Prioritize D-SNP enrollment outreach and integrated care coordination programs.")
    if high_chronic_counties > 10:
        recommendations.append(f"**Chronic Care Management**: {high_chronic_counties} counties show chronic burden index above the 75th percentile. Deploy value-based care models, remote monitoring, and care management resources.")
    recommendations.append("**Community Health Partnerships**: Engage county health departments and community organizations in high-priority geographies to address social determinants (food access, transportation).")
    recommendations.append("**Data-Driven Outreach**: Use this priority ranking to sequence direct mail, telephonic, and field outreach campaigns by county, targeting months before Annual Enrollment Period (AEP).")

    for rec in recommendations:
        st.markdown(f"- {rec}")

    st.markdown("---")
    st.markdown("### Outreach Strategy")
    st.markdown("""
1. **Phase 1 — Immediate**: Focus field marketing and broker activation on top 10 priority counties.
2. **Phase 2 — Near-term**: Launch D-SNP and LIS awareness campaigns in counties with dual-eligible rate > 25%.
3. **Phase 3 — Ongoing**: Establish chronic disease partnerships with health systems in counties with chronic burden index > 0.80.
""")

    st.markdown("---")
    st.markdown("### Risk Caveats & Data Limitations")
    st.markdown("""
- Medicare enrollment counts are point-in-time (January 2026) and may not reflect seasonal variation.
- CDC PLACES estimates are modeled from BRFSS surveys; small counties may have wider confidence intervals.
- Suppressed Medicare values (marked `*`) are excluded from calculations, which may understate counts in small counties.
- This tool is a **decision-support prototype** — not clinical guidance or regulatory reporting.
""")


def answer_question(question: str, df: pd.DataFrame) -> str:
    """Deterministic Q&A using pandas logic."""
    q = question.lower()

    # State-specific prioritization
    for state_name, abbr in [("california", "CA"), ("texas", "TX"), ("florida", "FL"),
                              ("new york", "NY"), ("ohio", "OH"), ("pennsylvania", "PA"),
                              ("illinois", "IL"), ("georgia", "GA"), ("michigan", "MI")]:
        if state_name in q and ("priorit" in q or "focus" in q or "target" in q or "which" in q):
            state_df = df[df["STATE"] == abbr]
            if state_df.empty:
                return f"No data found for {state_name.title()} in the current filtered view."
            top = state_df.head(5)
            counties = ", ".join([f"{r['COUNTY']} (Score: {r['OUTREACH_PRIORITY_SCORE']:.1f})" for _, r in top.iterrows()])
            return f"Top priority counties in {state_name.title()}: {counties}"

    # Dual eligible concentration
    if "dual" in q and ("high" in q or "concentration" in q or "where" in q):
        top_dual = df.nlargest(5, "DUAL_ELIGIBLE_RATE")
        counties = ", ".join([f"{r['COUNTY']}, {r['STATE']} ({r['DUAL_ELIGIBLE_RATE']:.0%})" for _, r in top_dual.iterrows()])
        return f"Counties with highest dual-eligible concentration: {counties}"

    # Diabetes + Medicare
    if "diabetes" in q and ("medicare" in q or "population" in q or "high" in q):
        if "DIABETES" in df.columns:
            high_diab = df[(df["DIABETES"] > df["DIABETES"].quantile(0.75)) & (df["TOT_BENES"] > df["TOT_BENES"].quantile(0.5))]
            top = high_diab.nlargest(5, "OUTREACH_PRIORITY_SCORE")
            if not top.empty:
                counties = ", ".join([f"{r['COUNTY']}, {r['STATE']} (Diabetes: {r['DIABETES']:.1f}%, Benes: {r['TOT_BENES']:,.0f})" for _, r in top.iterrows()])
                return f"Counties with high diabetes AND large Medicare population: {counties}"
        return "Unable to find matching counties for that combination."

    # General top priority
    if "priorit" in q or "top" in q or "highest" in q or "best" in q or "first" in q:
        top5 = df.head(5)
        lines = ["**Recommended Priority Geographies** (ranked by Outreach Priority Score):\n"]
        for rank, (_, r) in enumerate(top5.iterrows(), start=1):
            lines.append(f"{rank}. **{r['COUNTY']}, {r['STATE']}** — Score: {r['OUTREACH_PRIORITY_SCORE']:.1f}/100, "
                         f"Beneficiaries: {r['TOT_BENES']:,.0f}, Dual Rate: {r['DUAL_ELIGIBLE_RATE']:.0%}")
        lines.append("\n*Recommendation:* Begin field marketing, broker activation, and D-SNP outreach in these counties before the next Annual Enrollment Period.")
        return "\n".join(lines)

    # Why are these counties high risk?
    if "why" in q and ("high risk" in q or "risk" in q):
        top3 = df.head(3)
        lines = ["**Risk Analysis — Top Priority Counties:**\n"]
        for rank, (_, r) in enumerate(top3.iterrows(), start=1):
            drivers = []
            if pd.notna(r.get("DUAL_ELIGIBLE_RATE")) and r["DUAL_ELIGIBLE_RATE"] > 0.25:
                drivers.append(f"dual-eligible concentration at {r['DUAL_ELIGIBLE_RATE']:.0%} (indicating complex care needs and D-SNP opportunity)")
            if pd.notna(r.get("CHRONIC_BURDEN_INDEX")) and r["CHRONIC_BURDEN_INDEX"] > 0.7:
                drivers.append(f"chronic burden index of {r['CHRONIC_BURDEN_INDEX']:.2f} (top quartile nationally)")
            if pd.notna(r.get("DIABETES")) and r["DIABETES"] > 14:
                drivers.append(f"diabetes prevalence at {r['DIABETES']:.1f}% (above national average)")
            if pd.notna(r.get("TOT_BENES")) and r["TOT_BENES"] > 30000:
                drivers.append(f"large addressable Medicare population ({r['TOT_BENES']:,.0f} beneficiaries)")
            if not drivers:
                drivers.append("combined risk factors exceeding the national median across multiple dimensions")
            lines.append(f"{rank}. **{r['COUNTY']}, {r['STATE']}**: {'; '.join(drivers)}")
        lines.append("\n*Clinical implication:* These counties have overlapping chronic disease burden, socioeconomic vulnerability, and large Medicare populations — creating both higher utilization risk and greater outreach ROI.")
        return "\n".join(lines)

    # What actions should a payer take?
    if "action" in q or "payer" in q or "next" in q or "do" in q or "should" in q:
        avg_dual = df["DUAL_ELIGIBLE_RATE"].mean()
        avg_ma = df["MA_PENETRATION"].mean()
        high_chronic = (df["CHRONIC_BURDEN_INDEX"] > 0.75).sum()
        lines = ["**Recommended Payer Actions:**\n"]
        if avg_ma < 0.5:
            lines.append(f"1. **Network Expansion**: Average MA penetration in this view is {avg_ma:.0%}. Expand MA plan availability, strengthen provider networks, and activate broker channels in underserved counties.")
        if avg_dual > 0.15:
            lines.append(f"2. **D-SNP Enrollment**: Average dual-eligible rate is {avg_dual:.0%}. Launch targeted D-SNP enrollment campaigns, integrate care coordination with Medicaid MCOs, and deploy community health workers.")
        if high_chronic > 5:
            lines.append(f"3. **Chronic Care Management**: {high_chronic} counties exceed the 75th percentile for chronic burden. Invest in value-based care models, remote patient monitoring, and disease management programs for diabetes, COPD, and CHD.")
        lines.append("4. **Social Determinants Strategy**: Address food insecurity and transportation barriers through community health partnerships and supplemental benefit design.")
        lines.append("5. **Outreach Sequencing**: Use the Outreach Priority Score to sequence direct mail, telephonic outreach, and field events — starting 90 days before AEP in the highest-ranked counties.")
        lines.append("\n*Timeline:* Actions 1-2 should begin immediately for next enrollment cycle. Actions 3-5 are ongoing population health investments.")
        return "\n".join(lines)

    # COPD
    if "copd" in q:
        if "COPD" in df.columns:
            top_copd = df.nlargest(5, "COPD")
            counties = ", ".join([f"{r['COUNTY']}, {r['STATE']} ({r['COPD']:.1f}%)" for _, r in top_copd.iterrows()])
            return f"Counties with highest COPD prevalence: {counties}"

    # MA penetration
    if "ma penetration" in q or "medicare advantage" in q:
        if "low" in q:
            low_ma = df.nsmallest(5, "MA_PENETRATION")
            counties = ", ".join([f"{r['COUNTY']}, {r['STATE']} ({r['MA_PENETRATION']:.0%})" for _, r in low_ma.iterrows()])
            return f"Counties with lowest MA penetration (growth opportunity): {counties}"
        else:
            high_ma = df.nlargest(5, "MA_PENETRATION")
            counties = ", ".join([f"{r['COUNTY']}, {r['STATE']} ({r['MA_PENETRATION']:.0%})" for _, r in high_ma.iterrows()])
            return f"Counties with highest MA penetration: {counties}"

    return ("I can answer questions about county priorities, dual-eligible concentration, chronic disease prevalence, "
            "MA penetration, and state-level targeting. Try asking: 'Which counties should we prioritize in Florida?' "
            "or 'Where is dual eligible concentration highest?'")


# =============================================================================
# TAB 6: DATA COPILOT (CHATBOT)
# =============================================================================
def get_snowflake_connection():
    """Create a Snowflake connection using environment variables or local config."""
    try:
        import snowflake.connector
        account = os.environ.get("SNOWFLAKE_ACCOUNT", "")
        user = os.environ.get("SNOWFLAKE_USER", "")
        if not account or not user:
            # Fall back to local connections.toml config
            conn = snowflake.connector.connect(
                connection_name="default",
            )
        else:
            conn = snowflake.connector.connect(
                account=account,
                user=user,
                authenticator="externalbrowser",
            )
        return conn
    except Exception:
        return None


def build_data_context(df):
    """Build a concise text summary of the filtered dataset for the LLM."""
    if df.empty:
        return "No data available in the current filtered view."

    total_counties = len(df)
    total_benes = df["TOT_BENES"].sum()
    avg_ma = df["MA_PENETRATION"].mean()
    avg_dual = df["DUAL_ELIGIBLE_RATE"].mean()
    avg_chronic = df["CHRONIC_BURDEN_INDEX"].mean()

    top5 = df.head(5)
    top5_text = "\n".join([
        f"  {i+1}. {r['COUNTY']}, {r['STATE']} — Score: {r['OUTREACH_PRIORITY_SCORE']:.1f}, "
        f"Benes: {r['TOT_BENES']:,.0f}, Dual Rate: {r['DUAL_ELIGIBLE_RATE']:.0%}, "
        f"Chronic Burden: {r['CHRONIC_BURDEN_INDEX']:.2f}"
        for i, (_, r) in enumerate(top5.iterrows())
    ])

    states_list = ", ".join(sorted(df["STATE"].unique())[:15])

    context = f"""You are a healthcare analytics assistant for the Medicare Access & Chronic Risk Copilot.
You help healthcare payer teams understand county-level Medicare data to plan outreach, care management, and network strategy.

CURRENT DATA CONTEXT (filtered view):
- Counties in view: {total_counties}
- Total Medicare beneficiaries: {total_benes:,.0f}
- Average MA penetration: {avg_ma:.1%}
- Average dual-eligible rate: {avg_dual:.1%}
- Average chronic burden index: {avg_chronic:.2f} (scale 0-1)
- States represented: {states_list}

TOP 5 PRIORITY COUNTIES:
{top5_text}

AVAILABLE METRICS PER COUNTY:
- TOT_BENES: Total Medicare beneficiaries
- MA_PENETRATION: Medicare Advantage enrollment rate
- DUAL_ELIGIBLE_RATE: Dual-eligible (Medicare + Medicaid) rate
- LIS_RATE: Low-Income Subsidy enrollment rate
- AGE_75_PLUS_RATE: Percentage of beneficiaries aged 75+
- CHRONIC_BURDEN_INDEX: Composite chronic disease percentile (0-1)
- SOCIAL_NEED_INDEX: Composite social determinants percentile (0-1)
- OUTREACH_PRIORITY_SCORE: Final priority score (0-100)
- Disease prevalence: DIABETES, BPHIGH, CHD, COPD, STROKE, OBESITY, CSMOKING, LPA, DEPRESSION, FOODINSECU, LACKTRPT, MOBILITY

INSTRUCTIONS:
- Answer questions about county priorities, chronic disease burden, dual-eligible populations, outreach strategy, and Medicare market analysis.
- When asked about specific counties or states, reference the data context above.
- Provide actionable healthcare payer recommendations when appropriate.
- Be concise and professional. Use bullet points for clarity.
- If the question cannot be answered from the data, say so honestly.
"""
    return context


def call_cortex_llm(messages, conn):
    """Call Snowflake Cortex Complete via SQL."""
    try:
        # Build the prompt from messages
        prompt_parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt_parts.append(f"[SYSTEM]: {content}")
            elif role == "user":
                prompt_parts.append(f"[USER]: {content}")
            elif role == "assistant":
                prompt_parts.append(f"[ASSISTANT]: {content}")
        prompt_parts.append("[ASSISTANT]:")
        full_prompt = "\n\n".join(prompt_parts)

        # Escape single quotes for SQL
        escaped_prompt = full_prompt.replace("'", "''")

        # Truncate if too long (Cortex has token limits)
        if len(escaped_prompt) > 12000:
            escaped_prompt = escaped_prompt[:12000]

        cursor = conn.cursor()
        sql = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-70b', '{escaped_prompt}')"
        cursor.execute(sql)
        result = cursor.fetchone()
        cursor.close()

        if result and result[0]:
            return result[0]
        return None
    except Exception as e:
        return f"LLM Error: {str(e)}"


def render_chatbot(df):
    st.markdown("## Data Copilot")
    st.markdown("Chat with your Medicare & chronic risk data using Snowflake Cortex AI.")

    # Initialize session state for chat
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "cortex_conn" not in st.session_state:
        st.session_state.cortex_conn = None
    if "cortex_status" not in st.session_state:
        st.session_state.cortex_status = "not_connected"

    # Connection status and connect button
    if st.session_state.cortex_status != "connected":
        st.info("Connect to Snowflake Cortex to enable AI-powered responses. A browser window will open for authentication.")
        if st.button("Connect to Snowflake Cortex"):
            with st.spinner("Connecting to Snowflake (browser auth)..."):
                conn = get_snowflake_connection()
                if conn:
                    st.session_state.cortex_conn = conn
                    st.session_state.cortex_status = "connected"
                    st.rerun()
                else:
                    st.error("Failed to connect. The chatbot will use deterministic answers instead.")
                    st.session_state.cortex_status = "fallback"

    if st.session_state.cortex_status == "connected":
        st.success("Connected to Snowflake Cortex (llama3.1-70b)")
    elif st.session_state.cortex_status == "fallback":
        st.warning("Running in fallback mode (deterministic answers, no LLM).")

    st.markdown("---")

    # Starter suggestions
    if not st.session_state.chat_messages:
        st.markdown("**Try asking:**")
        sug_cols = st.columns(3)
        with sug_cols[0]:
            if st.button("Which counties should we prioritize?", key="sug1", use_container_width=True):
                st.session_state.chat_messages.append({"role": "user", "content": "Which counties should we prioritize?"})
                st.rerun()
        with sug_cols[1]:
            if st.button("What are the top risk drivers?", key="sug2", use_container_width=True):
                st.session_state.chat_messages.append({"role": "user", "content": "What are the top risk drivers in the highest priority counties?"})
                st.rerun()
        with sug_cols[2]:
            if st.button("Recommend a D-SNP strategy", key="sug3", use_container_width=True):
                st.session_state.chat_messages.append({"role": "user", "content": "Recommend a D-SNP enrollment strategy based on the dual-eligible data."})
                st.rerun()

    # Display chat history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("Ask about your Medicare & chronic risk data...")

    if user_input:
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if st.session_state.cortex_status == "connected" and st.session_state.cortex_conn:
                    # Build messages with system context
                    data_context = build_data_context(df)
                    llm_messages = [{"role": "system", "content": data_context}]
                    # Include last 6 messages for context window
                    for m in st.session_state.chat_messages[-6:]:
                        llm_messages.append(m)

                    response = call_cortex_llm(llm_messages, st.session_state.cortex_conn)
                    if response and not response.startswith("LLM Error"):
                        st.markdown(response)
                        st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    else:
                        # Fallback on error
                        fallback = answer_question(user_input, df)
                        st.markdown(fallback)
                        st.session_state.chat_messages.append({"role": "assistant", "content": fallback})
                        if response and response.startswith("LLM Error"):
                            st.caption(f"(Cortex unavailable: {response}. Using deterministic fallback.)")
                else:
                    # Deterministic fallback
                    fallback = answer_question(user_input, df)
                    st.markdown(fallback)
                    st.session_state.chat_messages.append({"role": "assistant", "content": fallback})

    # Clear chat button
    if st.session_state.chat_messages:
        if st.button("Clear conversation", key="clear_chat"):
            st.session_state.chat_messages = []
            st.rerun()


# =============================================================================
# TAB 5: DATA DICTIONARY
# =============================================================================
def render_data_dictionary():
    st.markdown("## Data Dictionary & Methodology")

    st.markdown("### Data Sources")
    st.markdown("""
| Source | Description | Vintage |
|--------|-------------|---------|
| CMS Medicare Monthly Enrollment | County-level beneficiary counts by plan type, demographics, and program eligibility | January 2026 |
| CDC PLACES | County-level modeled estimates of chronic disease prevalence from BRFSS | 2023 release |
""")

    st.markdown("### Key Medicare Fields")
    st.markdown("""
- **TOT_BENES**: Total Medicare beneficiaries enrolled in the county.
- **MA_AND_OTH_BENES**: Beneficiaries enrolled in Medicare Advantage or other health plans.
- **ORGNL_MDCR_BENES**: Beneficiaries enrolled in Original (Fee-for-Service) Medicare.
- **DUAL_TOT_BENES**: Beneficiaries eligible for both Medicare and Medicaid.
- **PRSCRPTN_DRUG_TOT_BENES**: Beneficiaries enrolled in Part D prescription drug coverage.
- **LIS beneficiaries**: Low-Income Subsidy recipients who receive help paying Part D premiums and copays.
""")

    st.markdown("### Key CDC PLACES Measures")
    st.markdown("""
- **DIABETES**: Adults aged 18+ with diagnosed diabetes (age-adjusted prevalence).
- **BPHIGH**: Adults with high blood pressure.
- **CHD**: Adults with coronary heart disease.
- **COPD**: Adults with chronic obstructive pulmonary disease.
- **OBESITY**: Adults with BMI >= 30.
- **FOODINSECU**: Adults who are food insecure.
- **LACKTRPT**: Adults who lack reliable transportation.
- **MOBILITY**: Adults with mobility disability.
""")

    st.markdown("### Derived Metrics")
    st.markdown("""
- **Chronic Burden Index**: Average percentile rank across 9 chronic disease indicators.
- **Social Need Index**: Average percentile rank of food insecurity, transportation barriers, and mobility disability.
- **Medicare Opportunity Index**: Percentile rank by total beneficiary count (larger = more opportunity).
- **Outreach Priority Score** (0-100): Weighted composite of Medicare opportunity (30%), chronic burden (25%), dual-eligible rate (20%), social need (15%), and LIS rate (10%).
""")

    st.markdown("### Data Quality Notes")
    st.markdown("""
- Suppressed Medicare values (marked `*` in source) are treated as missing/null.
- Numeric conversions use `pandas.to_numeric(errors='coerce')` to handle non-numeric entries safely.
- FIPS codes are zero-padded to 5 characters for consistent county matching.
- CDC PLACES uses age-adjusted prevalence to enable cross-county comparison.
- This is a **decision-support prototype** — not clinical guidance or regulatory reporting.
""")


# =============================================================================
# DATA VALIDATION
# =============================================================================
def render_data_validation(df):
    with st.expander("Data Validation Summary"):
        medicare_raw = load_medicare()
        places_raw = load_places()
        c1, c2, c3 = st.columns(3)
        c1.metric("Medicare County Rows", f"{len(medicare_raw):,}")
        c2.metric("PLACES County Rows", f"{len(places_raw):,}")
        c3.metric("Joined Counties", f"{len(df):,}")
        # Missing values
        missing_pct = df[MEDICARE_FIELDS[0:5]].isnull().mean() * 100
        st.markdown("**Missing Value % (key Medicare fields):**")
        missing_str = ", ".join([f"{col}: {pct:.1f}%" for col, pct in missing_pct.items()])
        st.text(missing_str)
        st.caption(f"Files loaded from: `{DATA_DIR}`")


# =============================================================================
# MAIN
# =============================================================================
def main():
    # Header and demo guide
    render_header()

    # Load data
    full_df = build_dataset()

    if full_df.empty:
        st.error("Failed to load or merge datasets. Check file paths and data formats.")
        st.markdown(f"**Expected Medicare file:** `{MEDICARE_FILE}`")
        st.markdown(f"**Expected PLACES file:** `{PLACES_FILE}`")
        return

    # Apply sidebar filters
    filtered_df = render_sidebar(full_df)

    # Data validation
    render_data_validation(full_df)

    # Tabs
    tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Mission Control",
        "Executive Overview",
        "County Prioritization",
        "Chronic Risk Explorer",
        "AI Action Summary",
        "Data Copilot",
        "Data Dictionary",
    ])

    with tab0:
        render_mission_control(filtered_df)
    with tab1:
        render_executive_overview(filtered_df, full_df)
    with tab2:
        render_county_prioritization(filtered_df)
    with tab3:
        render_chronic_explorer(filtered_df)
    with tab4:
        render_ai_summary(filtered_df)
    with tab5:
        render_chatbot(filtered_df)
    with tab6:
        render_data_dictionary()


if __name__ == "__main__":
    main()
