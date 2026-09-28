import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, inspect
from pathlib import Path

# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(page_title="Fitness & Wellness Analytics", page_icon="🏃", layout="wide")

# =========================================================
# SQLITE DATABASE
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "fitness_analytics.db"
DATA_DIR = BASE_DIR / "data"

CSV_PATHS = {
    "daily_activity": [DATA_DIR / "dailyActivity_merged.csv", BASE_DIR / "dailyActivity_merged.csv"],
    "sleep_data": [DATA_DIR / "sleepDay_merged.csv", BASE_DIR / "sleepDay_merged.csv"],
    "weight_data": [DATA_DIR / "weightLogInfo_merged.csv", BASE_DIR / "weightLogInfo_merged.csv"],
}

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def find_csv(table_name):
    for path in CSV_PATHS[table_name]:
        if path.exists():
            return path
    return None


def initialize_database():
    """Create SQLite tables/views automatically if the database is missing."""
    inspector = inspect(engine)
    required = {"daily_activity", "sleep_data", "weight_data"}
    if required.issubset(set(inspector.get_table_names())):
        return

    missing = [name for name in required if find_csv(name) is None]
    if missing:
        st.error("SQLite database is not initialized and these CSV files are missing: " + ", ".join(missing))
        st.info("Place fitness_analytics.db beside app.py, or place the three source CSV files in a data/ folder.")
        st.stop()

    daily = pd.read_csv(find_csv("daily_activity"))
    sleep = pd.read_csv(find_csv("sleep_data"))
    weight = pd.read_csv(find_csv("weight_data"))

    daily["ActivityDate"] = pd.to_datetime(daily["ActivityDate"], errors="coerce").dt.strftime("%Y-%m-%d")
    sleep["SleepDay"] = pd.to_datetime(sleep["SleepDay"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    weight["Date"] = pd.to_datetime(weight["Date"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

    daily.to_sql("daily_activity", engine, if_exists="replace", index=False)
    sleep.to_sql("sleep_data", engine, if_exists="replace", index=False)
    weight.to_sql("weight_data", engine, if_exists="replace", index=False)

    with engine.begin() as conn:
        conn.exec_driver_sql("DROP VIEW IF EXISTS activity_clean")
        conn.exec_driver_sql("""
            CREATE VIEW activity_clean AS
            SELECT Id, ActivityDate,
                CASE strftime('%w', ActivityDate)
                    WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday'
                    WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday'
                    WHEN '5' THEN 'Friday' WHEN '6' THEN 'Saturday'
                END AS DayName,
                CAST(strftime('%w', ActivityDate) AS INTEGER) AS DayNumber,
                TotalSteps, TotalDistance, TrackerDistance, LoggedActivitiesDistance,
                VeryActiveDistance, ModeratelyActiveDistance, LightActiveDistance,
                SedentaryActiveDistance, VeryActiveMinutes, FairlyActiveMinutes,
                LightlyActiveMinutes, SedentaryMinutes, Calories,
                (COALESCE(VeryActiveMinutes,0)+COALESCE(FairlyActiveMinutes,0)+COALESCE(LightlyActiveMinutes,0)) AS ActiveMinutes,
                (COALESCE(VeryActiveMinutes,0)+COALESCE(FairlyActiveMinutes,0)) AS ModerateVigorousMinutes
            FROM daily_activity
        """)
        conn.exec_driver_sql("DROP VIEW IF EXISTS activity_classification")
        conn.exec_driver_sql("""
            CREATE VIEW activity_classification AS
            SELECT *, CASE
                WHEN TotalSteps < 5000 THEN 'Sedentary'
                WHEN TotalSteps < 7500 THEN 'Low Active'
                WHEN TotalSteps < 10000 THEN 'Moderately Active'
                ELSE 'Highly Active'
            END AS ActivityLevel
            FROM activity_clean
        """)
        conn.exec_driver_sql("DROP VIEW IF EXISTS sleep_clean")
        conn.exec_driver_sql("""
            CREATE VIEW sleep_clean AS
            SELECT Id, date(SleepDay) AS SleepDate, TotalSleepRecords,
                TotalMinutesAsleep, TotalTimeInBed,
                ROUND(TotalMinutesAsleep / 60.0, 2) AS SleepHours,
                ROUND(CASE WHEN TotalTimeInBed IS NULL OR TotalTimeInBed = 0 THEN NULL
                    ELSE TotalMinutesAsleep * 100.0 / TotalTimeInBed END, 2) AS SleepEfficiency
            FROM sleep_data
        """)
        conn.exec_driver_sql("DROP VIEW IF EXISTS weight_clean")
        conn.exec_driver_sql("""
            CREATE VIEW weight_clean AS
            SELECT Id, Date AS WeightDate, WeightKg, WeightPounds, Fat, BMI,
                IsManualReport, LogId,
                CASE WHEN BMI IS NULL THEN 'Unknown'
                    WHEN BMI < 18.5 THEN 'Underweight'
                    WHEN BMI < 25 THEN 'Normal'
                    WHEN BMI < 30 THEN 'Overweight'
                    ELSE 'Obesity' END AS BMICategory
            FROM weight_data
        """)

initialize_database()

# =========================================================
# QUERY HELPER
# =========================================================
@st.cache_data
def run_query(query):
    try:
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error("Database query error. Check the SQLite database and table/view names.")
        st.exception(e)
        return pd.DataFrame()

# =========================================================
# HEADER
# =========================================================
st.title("🏃 Fitness & Wellness Analytics Dashboard")
st.markdown("""
**SQL-powered fitness analytics dashboard** using activity, sleep and weight data.
Pandas is used for exploratory analysis and SQL is used for business insight calculations.
""")

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("Dashboard Controls")
activity_levels = st.sidebar.multiselect(
    "Activity Level",
    ["Sedentary", "Low Active", "Moderately Active", "Highly Active"],
    default=["Sedentary", "Low Active", "Moderately Active", "Highly Active"]
)
st.sidebar.markdown("---")
st.sidebar.info("Data source: Fitness tracker activity, sleep and weight logs.")

# =========================================================
# KPI SECTION
# =========================================================
kpi_query = """
SELECT COUNT(DISTINCT Id) AS Users, ROUND(AVG(TotalSteps), 0) AS AvgSteps,
ROUND(AVG(TotalDistance), 2) AS AvgDistance, ROUND(AVG(Calories), 0) AS AvgCalories,
ROUND(AVG(SedentaryMinutes), 0) AS AvgSedentaryMinutes
FROM daily_activity;
"""
kpi = run_query(kpi_query)
if not kpi.empty:
    row = kpi.iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 Users", f"{int(row['Users']):,}")
    c2.metric("👣 Avg Steps", f"{int(row['AvgSteps']):,}")
    c3.metric("📍 Avg Distance", f"{row['AvgDistance']:.2f} km")
    c4.metric("🔥 Avg Calories", f"{int(row['AvgCalories']):,}")
    c5.metric("🪑 Avg Sedentary", f"{int(row['AvgSedentaryMinutes']):,} min")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["🏠 Overview", "🏃 Activity", "😴 Sleep", "⚖️ Weight & BMI"])

# =========================================================
# TAB 1 - OVERVIEW
# =========================================================
with tab1:
    st.header("🏠 Fitness Overview")
    col1, col2 = st.columns(2)

    with col1:
        df = run_query("""
        SELECT DayName, DayNumber, ROUND(AVG(TotalSteps), 0) AS AvgSteps
        FROM activity_clean GROUP BY DayName, DayNumber ORDER BY DayNumber;
        """)
        if not df.empty:
            fig = px.bar(df, x="DayName", y="AvgSteps", title="Average Steps by Day", text_auto=True)
            fig.update_layout(xaxis_title="Day", yaxis_title="Average Steps")
            st.plotly_chart(fig, use_container_width=True)
            highest_day = df.loc[df["AvgSteps"].idxmax(), "DayName"]
            st.info(f"**Insight:** {highest_day} has the highest average daily steps in the activity dataset.")

    with col2:
        df = run_query("""
        SELECT ActivityLevel, COUNT(*) AS Records
        FROM activity_classification GROUP BY ActivityLevel ORDER BY Records DESC;
        """)
        if not df.empty:
            selected_df = df[df["ActivityLevel"].isin(activity_levels)]
            if not selected_df.empty:
                fig = px.pie(selected_df, names="ActivityLevel", values="Records", hole=0.45, title="Activity Level Distribution")
                st.plotly_chart(fig, use_container_width=True)
                top_level = selected_df.loc[selected_df["Records"].idxmax(), "ActivityLevel"]
                st.info(f"**Insight:** {top_level} is the most common activity category among the selected categories.")

    monthly = run_query("""
    SELECT strftime('%Y-%m', ActivityDate) AS Month,
           ROUND(AVG(TotalSteps), 0) AS AvgSteps,
           ROUND(AVG(Calories), 0) AS AvgCalories
    FROM daily_activity WHERE ActivityDate IS NOT NULL
    GROUP BY Month ORDER BY Month;
    """)
    if not monthly.empty:
        fig = px.line(monthly, x="Month", y="AvgSteps", markers=True, title="Monthly Average Steps")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("💡 Key Business Insights")
    st.markdown("""
    - Monitor activity patterns by day and month to identify periods of stronger or weaker engagement.
    - Activity-level segmentation can support personalized fitness challenges and reminders.
    - Combining activity and sleep behavior can support a broader wellness experience.
    """)

# =========================================================
# TAB 2 - ACTIVITY
# =========================================================
with tab2:
    st.header("🏃 Activity Analysis")
    intensity = run_query("""
    SELECT ROUND(AVG(VeryActiveMinutes), 2) AS VeryActive,
           ROUND(AVG(FairlyActiveMinutes), 2) AS FairlyActive,
           ROUND(AVG(LightlyActiveMinutes), 2) AS LightlyActive,
           ROUND(AVG(SedentaryMinutes), 2) AS Sedentary
    FROM daily_activity;
    """)
    if not intensity.empty:
        intensity_long = pd.DataFrame({
            "Activity Type": ["Very Active", "Fairly Active", "Lightly Active", "Sedentary"],
            "Average Minutes": [intensity.iloc[0]["VeryActive"], intensity.iloc[0]["FairlyActive"], intensity.iloc[0]["LightlyActive"], intensity.iloc[0]["Sedentary"]]
        })
        fig = px.bar(intensity_long, x="Activity Type", y="Average Minutes", title="Average Activity Minutes by Intensity", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
        highest = intensity_long.loc[intensity_long["Average Minutes"].idxmax()]
        st.info(f"**Insight:** {highest['Activity Type']} has the highest average duration at {highest['Average Minutes']:.1f} minutes.")

    col1, col2 = st.columns(2)
    with col1:
        scatter = run_query("""
        SELECT TotalSteps, Calories FROM daily_activity
        WHERE TotalSteps IS NOT NULL AND Calories IS NOT NULL;
        """)
        if not scatter.empty:
            fig = px.scatter(scatter, x="TotalSteps", y="Calories", title="Steps vs Calories", trendline="ols")
            st.plotly_chart(fig, use_container_width=True)
            corr = scatter[["TotalSteps", "Calories"]].corr().iloc[0, 1]
            st.info(f"**Insight:** The Pearson correlation between steps and calories in the available records is {corr:.2f}.")

    with col2:
        top_users = run_query("""
        SELECT Id, ROUND(AVG(TotalSteps), 0) AS AvgSteps
        FROM daily_activity GROUP BY Id ORDER BY AvgSteps DESC LIMIT 10;
        """)
        if not top_users.empty:
            fig = px.bar(top_users, x="Id", y="AvgSteps", title="Top 10 Users by Average Steps", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

    sedentary = run_query("""
    SELECT Id, ROUND(AVG(SedentaryMinutes), 0) AS AvgSedentaryMinutes
    FROM daily_activity GROUP BY Id ORDER BY AvgSedentaryMinutes DESC LIMIT 10;
    """)
    if not sedentary.empty:
        fig = px.bar(sedentary, x="Id", y="AvgSedentaryMinutes", title="Top 10 Users by Average Sedentary Minutes", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

# =========================================================
# TAB 3 - SLEEP
# =========================================================
with tab3:
    st.header("😴 Sleep Analysis")
    sleep_kpi = run_query("""
    SELECT COUNT(DISTINCT Id) AS Users,
           ROUND(AVG(TotalMinutesAsleep) / 60.0, 2) AS AvgSleepHours,
           ROUND(AVG(TotalTimeInBed) / 60.0, 2) AS AvgTimeInBed,
           ROUND(AVG(CASE WHEN TotalTimeInBed IS NULL OR TotalTimeInBed = 0 THEN NULL
                          ELSE TotalMinutesAsleep * 100.0 / TotalTimeInBed END), 2) AS AvgSleepEfficiency
    FROM sleep_data;
    """)
    if not sleep_kpi.empty:
        row = sleep_kpi.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("😴 Avg Sleep", f"{row['AvgSleepHours']:.2f} hrs")
        c2.metric("🛏️ Avg Time in Bed", f"{row['AvgTimeInBed']:.2f} hrs")
        c3.metric("📊 Sleep Efficiency", f"{row['AvgSleepEfficiency']:.1f}%")

    col1, col2 = st.columns(2)
    with col1:
        sleep_category = run_query("""
        SELECT CASE WHEN TotalMinutesAsleep < 360 THEN 'Less than 6 hours'
                    WHEN TotalMinutesAsleep < 420 THEN '6-7 hours'
                    WHEN TotalMinutesAsleep < 480 THEN '7-8 hours'
                    ELSE '8+ hours' END AS SleepCategory,
               COUNT(*) AS Records
        FROM sleep_data GROUP BY SleepCategory ORDER BY Records DESC;
        """)
        if not sleep_category.empty:
            fig = px.bar(sleep_category, x="SleepCategory", y="Records", title="Sleep Duration Distribution", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        sleep_activity = run_query("""
        SELECT a.TotalSteps, a.Calories, s.SleepHours
        FROM activity_clean a JOIN sleep_clean s
          ON a.Id = s.Id AND a.ActivityDate = s.SleepDate;
        """)
        if not sleep_activity.empty:
            fig = px.scatter(sleep_activity, x="SleepHours", y="TotalSteps", size="Calories", title="Sleep Hours vs Total Steps", hover_data=["Calories"])
            st.plotly_chart(fig, use_container_width=True)
            corr = sleep_activity[["SleepHours", "TotalSteps"]].corr().iloc[0, 1]
            st.info(f"**Insight:** The Pearson correlation between sleep hours and total steps in the matched records is {corr:.2f}.")

    sleep_behavior = run_query("""
    SELECT CASE WHEN s.SleepHours < 6 THEN 'Less than 6 hours'
                WHEN s.SleepHours < 7 THEN '6-7 hours'
                WHEN s.SleepHours < 8 THEN '7-8 hours'
                ELSE '8+ hours' END AS SleepCategory,
           ROUND(AVG(a.Calories), 0) AS AvgCalories,
           ROUND(AVG(a.TotalSteps), 0) AS AvgSteps
    FROM activity_clean a JOIN sleep_clean s
      ON a.Id = s.Id AND a.ActivityDate = s.SleepDate
    GROUP BY SleepCategory ORDER BY SleepCategory;
    """)
    if not sleep_behavior.empty:
        fig = px.bar(sleep_behavior, x="SleepCategory", y="AvgCalories", title="Average Calories by Sleep Category", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

# =========================================================
# TAB 4 - WEIGHT & BMI
# =========================================================
with tab4:
    st.header("⚖️ Weight & BMI Analysis")
    weight_kpi = run_query("""
    SELECT COUNT(DISTINCT Id) AS Users, ROUND(AVG(WeightKg), 2) AS AvgWeightKg, ROUND(AVG(BMI), 2) AS AvgBMI
    FROM weight_data;
    """)
    if not weight_kpi.empty:
        row = weight_kpi.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("👥 Users", f"{int(row['Users']):,}")
        c2.metric("⚖️ Avg Weight", f"{row['AvgWeightKg']:.2f} kg")
        c3.metric("📏 Avg BMI", f"{row['AvgBMI']:.2f}")

    col1, col2 = st.columns(2)
    with col1:
        weight_trend = run_query("""
        SELECT date(WeightDate) AS WeightDate, ROUND(AVG(WeightKg), 2) AS AvgWeightKg
        FROM weight_clean WHERE WeightKg IS NOT NULL
        GROUP BY date(WeightDate) ORDER BY WeightDate;
        """)
        if not weight_trend.empty:
            fig = px.line(weight_trend, x="WeightDate", y="AvgWeightKg", markers=True, title="Average Weight Trend")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        bmi = run_query("""
        SELECT BMICategory, COUNT(*) AS Records FROM weight_clean
        WHERE BMICategory <> 'Unknown' GROUP BY BMICategory ORDER BY Records DESC;
        """)
        if not bmi.empty:
            fig = px.pie(bmi, names="BMICategory", values="Records", hole=0.45, title="BMI Category Distribution")
            st.plotly_chart(fig, use_container_width=True)

    st.caption("BMI categories are descriptive groupings of the dataset and should not be interpreted as an individual medical diagnosis.")

# =========================================================
# FOOTER
# =========================================================
st.markdown("---")
st.subheader("💡 Business Recommendations")
st.markdown("""
**1. Personalized activity goals**  
Use activity-level segmentation to tailor daily or weekly goals to different user behavior patterns.

**2. Encourage movement**  
Users with higher sedentary time can be targeted with reminders, movement prompts and activity challenges.

**3. Promote sleep tracking**  
Integrate sleep metrics into the overall wellness experience so users can view activity and sleep together.

**4. Gamification**  
Consider step challenges, streaks, milestones and achievement badges to support continued engagement.

**5. Integrated wellness dashboard**  
Combine activity, sleep and weight tracking into one personalized wellness view.
""")
st.caption("Fitness & Wellness Analytics | SQLite + Pandas + Streamlit")
