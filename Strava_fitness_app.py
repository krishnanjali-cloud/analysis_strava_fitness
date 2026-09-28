import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from urllib.parse import quote_plus

# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Fitness & Wellness Analytics",
    page_icon="🏃",
    layout="wide"
)

# =========================================================
# DATABASE CONNECTION
# =========================================================
# For local use, enter your MySQL credentials below.
# For Streamlit Cloud, use st.secrets instead.

DB_USER = st.secrets.get("DB_USER", "root")
DB_PASSWORD = st.secrets.get("DB_PASSWORD", "Jairam@12345")
DB_HOST = st.secrets.get("DB_HOST", "localhost")
DB_PORT = st.secrets.get("DB_PORT", "3306")
DB_NAME = st.secrets.get("DB_NAME", "fitness_analytics")

password_encoded = quote_plus(str(DB_PASSWORD))

engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{password_encoded}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    pool_pre_ping=True
)

# =========================================================
# HELPER FUNCTION
# =========================================================

@st.cache_data
def run_query(query):
    try:
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(
            "Database connection/query error. "
            "Check your MySQL credentials, database name, "
            "tables/views and that MySQL is running."
        )
        st.exception(e)
        return pd.DataFrame()


# =========================================================
# HEADER
# =========================================================

st.title("🏃 Fitness & Wellness Analytics Dashboard")
st.markdown(
    """
    **SQL-powered fitness analytics dashboard** using activity,
    sleep and weight data. Pandas is used for exploratory analysis
    and SQL is used for business insight calculations.
    """
)

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Dashboard Controls")

activity_levels = st.sidebar.multiselect(
    "Activity Level",
    [
        "Sedentary",
        "Low Active",
        "Moderately Active",
        "Highly Active"
    ],
    default=[
        "Sedentary",
        "Low Active",
        "Moderately Active",
        "Highly Active"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info(
    "Data source: Fitness tracker activity, sleep and weight logs."
)

# =========================================================
# KPI SECTION
# =========================================================

kpi_query = """
SELECT
    COUNT(DISTINCT Id) AS Users,
    ROUND(AVG(TotalSteps), 0) AS AvgSteps,
    ROUND(AVG(TotalDistance), 2) AS AvgDistance,
    ROUND(AVG(Calories), 0) AS AvgCalories,
    ROUND(AVG(SedentaryMinutes), 0) AS AvgSedentaryMinutes
FROM daily_activity;
"""

kpi = run_query(kpi_query)

if not kpi.empty:
    row = kpi.iloc[0]

    c1, c2, c3, c4, c5 = st.columns(5)

    users=row["Users"]
    c1.metric("👥 Users", f"{int(users):,}")

    avg_steps = row['AvgSteps']
    if pd.isna(avg_steps):
        c2.metric("👣 Avg Steps", "N/A")
    else:
        c2.metric("👣 Avg Steps", f"{int(avg_steps):,}")
    # c2.metric("👣 Avg Steps", f"{int(row['AvgSteps']):,}")
    c3.metric("📍 Avg Distance", f"{row['AvgDistance']:.2f} km")
    c4.metric("🔥 Avg Calories", f"{int(row['AvgCalories']):,}")
    c5.metric("🪑 Avg Sedentary", f"{int(row['AvgSedentaryMinutes']):,} min")

st.markdown("---")

# =========================================================
# TABS
# =========================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🏠 Overview",
        "🏃 Activity",
        "😴 Sleep",
        "⚖️ Weight & BMI"
    ]
)

# =========================================================
# TAB 1 - OVERVIEW
# =========================================================

with tab1:

    st.header("🏠 Fitness Overview")

    col1, col2 = st.columns(2)

    # ---------- WEEKDAY ACTIVITY ----------
    with col1:

        weekday_query = """
        SELECT
            DAYNAME(STR_TO_DATE(ActivityDate, '%%c/%%e/%%Y')) AS DayName,
            DAYOFWEEK(STR_TO_DATE(ActivityDate, '%%c/%%e/%%Y')) AS DayNumber,
            ROUND(AVG(TotalSteps), 0) AS AvgSteps
        FROM daily_activity
        WHERE ActivityDate IS NOT NULL
        GROUP BY
            DAYNAME(STR_TO_DATE(ActivityDate, '%%c/%%e/%%Y')),
            DAYOFWEEK(STR_TO_DATE(ActivityDate, '%%c/%%e/%%Y'))
        ORDER BY DayNumber
        """

        weekday_df = run_query(weekday_query)

        if not weekday_df.empty:
            fig = px.bar(
                    weekday_df,
                    x="DayName",
                    y="AvgSteps",
                    title="Average Steps by Day"
                )


            fig.update_layout(
                xaxis_title="Day",
                yaxis_title="Average Steps"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            highest_day = weekday_df.loc[
                weekday_df["AvgSteps"].idxmax(),
                "DayName"
            ]

            st.info(
                f"**Insight:** {highest_day} has the highest "
                "average daily steps in the activity dataset."
            )

    # ---------- ACTIVITY LEVEL ----------
    with col2:

        query = """
        SELECT
            ActivityLevel,
            COUNT(*) AS Records
        FROM activity_classification
        GROUP BY ActivityLevel
        ORDER BY Records DESC;
        """

        df = run_query(query)

        if not df.empty:

            selected_df = df[
                df["ActivityLevel"].isin(activity_levels)
            ]

            fig = px.pie(
                selected_df,
                names="ActivityLevel",
                values="Records",
                hole=0.45,
                title="Activity Level Distribution"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            top_level = selected_df.loc[
                selected_df["Records"].idxmax(),
                "ActivityLevel"
            ]

            st.info(
                f"**Insight:** {top_level} is the most common "
                "activity category among the selected categories."
            )

    # ---------- MONTHLY TREND ----------
    monthly_query = """
        SELECT
            DATE_FORMAT(
                STR_TO_DATE(ActivityDate, '%%c/%%e/%%Y'),
                '%%Y-%%m'
            ) AS Month,
            ROUND(AVG(TotalSteps), 0) AS AvgSteps
        FROM daily_activity
        WHERE ActivityDate IS NOT NULL
        GROUP BY
            DATE_FORMAT(
                STR_TO_DATE(ActivityDate, '%%c/%%e/%%Y'),
                '%%Y-%%m'
            )
        ORDER BY Month
        """

    monthly_df = run_query(monthly_query)

    if not monthly_df.empty:

        fig = px.bar(
        monthly_df,
        x="Month",
        y="AvgSteps",
        title="Monthly Average Steps"
    )


        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.subheader("💡 Key Business Insights")

    st.markdown(
        """
        - Monitor activity patterns by day and month to identify
          periods of stronger or weaker engagement.
        - Activity-level segmentation can support personalized
          fitness challenges and reminders.
        - Combining activity and sleep behavior can support a
          broader wellness experience.
        """
    )


# =========================================================
# TAB 2 - ACTIVITY
# =========================================================

with tab2:

    st.header("🏃 Activity Analysis")

    # ---------- ACTIVITY INTENSITY ----------
    query = """
    SELECT
        ROUND(AVG(VeryActiveMinutes), 2) AS VeryActive,
        ROUND(AVG(FairlyActiveMinutes), 2) AS FairlyActive,
        ROUND(AVG(LightlyActiveMinutes), 2) AS LightlyActive,
        ROUND(AVG(SedentaryMinutes), 2) AS Sedentary
    FROM daily_activity;
    """

    intensity = run_query(query)

    if not intensity.empty:

        intensity_long = pd.DataFrame({
            "Activity Type": [
                "Very Active",
                "Fairly Active",
                "Lightly Active",
                "Sedentary"
            ],
            "Average Minutes": [
                intensity.iloc[0]["VeryActive"],
                intensity.iloc[0]["FairlyActive"],
                intensity.iloc[0]["LightlyActive"],
                intensity.iloc[0]["Sedentary"]
            ]
        })

        fig = px.bar(
            intensity_long,
            x="Activity Type",
            y="Average Minutes",
            title="Average Activity Minutes by Intensity",
            text_auto=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        highest = intensity_long.loc[
            intensity_long["Average Minutes"].idxmax()
        ]

        st.info(
            f"**Insight:** {highest['Activity Type']} has the highest "
            f"average duration at {highest['Average Minutes']:.1f} minutes."
        )

    col1, col2 = st.columns(2)

    # ---------- STEPS VS CALORIES ----------
    with col1:

        query = """
        SELECT
            TotalSteps,
            Calories
        FROM daily_activity
        WHERE TotalSteps IS NOT NULL
          AND Calories IS NOT NULL;
        """

        scatter = run_query(query)

        if not scatter.empty:

            fig = px.scatter(
                scatter,
                x="TotalSteps",
                y="Calories",
                title="Steps vs Calories",
                trendline="ols"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            corr = scatter[
                ["TotalSteps", "Calories"]
            ].corr().iloc[0, 1]

            st.info(
                f"**Insight:** The Pearson correlation between "
                f"steps and calories in the available records is "
                f"{corr:.2f}."
            )

    # ---------- TOP USERS ----------
    with col2:

        query = """
        SELECT
            Id,
            ROUND(AVG(TotalSteps), 0) AS AvgSteps
        FROM daily_activity
        GROUP BY Id
        ORDER BY AvgSteps DESC
        LIMIT 10;
        """

        top_users = run_query(query)

        if not top_users.empty:

            fig = px.bar(
                top_users,
                x="Id",
                y="AvgSteps",
                title="Top 10 Users by Average Steps",
                text_auto=True
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    # ---------- SEDENTARY USERS ----------
    query = """
    SELECT
        Id,
        ROUND(AVG(SedentaryMinutes), 0) AS AvgSedentaryMinutes
    FROM daily_activity
    GROUP BY Id
    ORDER BY AvgSedentaryMinutes DESC
    LIMIT 10;
    """

    sedentary = run_query(query)

    if not sedentary.empty:

        fig = px.bar(
            sedentary,
            x="Id",
            y="AvgSedentaryMinutes",
            title="Top 10 Users by Average Sedentary Minutes",
            text_auto=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# =========================================================
# TAB 3 - SLEEP
# =========================================================

with tab3:

    st.header("😴 Sleep Analysis")

    sleep_query = """
    SELECT
        COUNT(DISTINCT Id) AS Users,
        ROUND(AVG(TotalMinutesAsleep) / 60, 2) AS AvgSleepHours,
        ROUND(AVG(TotalTimeInBed) / 60, 2) AS AvgTimeInBed,
        ROUND(
            AVG(TotalMinutesAsleep / NULLIF(TotalTimeInBed,0))
            * 100,
            2
        ) AS AvgSleepEfficiency
    FROM sleep_data;
    """

    sleep_kpi = run_query(sleep_query)

    if not sleep_kpi.empty:

        row = sleep_kpi.iloc[0]

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "😴 Avg Sleep",
            f"{row['AvgSleepHours']:.2f} hrs"
        )

        c2.metric(
            "🛏️ Avg Time in Bed",
            f"{row['AvgTimeInBed']:.2f} hrs"
        )

        c3.metric(
            "📊 Sleep Efficiency",
            f"{row['AvgSleepEfficiency']:.1f}%"
        )

    col1, col2 = st.columns(2)

    # ---------- SLEEP CATEGORY ----------
    with col1:

        query = """
        SELECT
            CASE
                WHEN TotalMinutesAsleep < 360
                    THEN 'Less than 6 hours'
                WHEN TotalMinutesAsleep < 420
                    THEN '6-7 hours'
                WHEN TotalMinutesAsleep < 480
                    THEN '7-8 hours'
                ELSE '8+ hours'
            END AS SleepCategory,
            COUNT(*) AS Records
        FROM sleep_data
        GROUP BY SleepCategory;
        """

        sleep_category = run_query(query)

        if not sleep_category.empty:

            fig = px.bar(
                sleep_category,
                x="SleepCategory",
                y="Records",
                title="Sleep Duration Distribution",
                text_auto=True
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    # ---------- SLEEP VS STEPS ----------
    with col2:

        query = """
        SELECT
            a.TotalSteps,
            a.Calories,
            s.SleepHours
        FROM activity_clean a
        JOIN sleep_clean s
            ON a.Id = s.Id
            AND a.ActivityDate = s.SleepDate;
        """

        sleep_activity = run_query(query)

        if not sleep_activity.empty:

            fig = px.scatter(
                sleep_activity,
                x="SleepHours",
                y="TotalSteps",
                size="Calories",
                title="Sleep Hours vs Total Steps",
                hover_data=["Calories"]
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            corr = sleep_activity[
                ["SleepHours", "TotalSteps"]
            ].corr().iloc[0, 1]

            st.info(
                f"**Insight:** The Pearson correlation between "
                f"sleep hours and total steps in the matched "
                f"records is {corr:.2f}."
            )

    # ---------- SLEEP VS CALORIES ----------
    query = """
    SELECT
        CASE
            WHEN s.SleepHours < 6 THEN 'Less than 6 hours'
            WHEN s.SleepHours < 7 THEN '6-7 hours'
            WHEN s.SleepHours < 8 THEN '7-8 hours'
            ELSE '8+ hours'
        END AS SleepCategory,
        ROUND(AVG(a.Calories), 0) AS AvgCalories,
        ROUND(AVG(a.TotalSteps), 0) AS AvgSteps
    FROM activity_clean a
    JOIN sleep_clean s
        ON a.Id = s.Id
        AND a.ActivityDate = s.SleepDate
    GROUP BY SleepCategory;
    """

    sleep_behavior = run_query(query)

    if not sleep_behavior.empty:

        fig = px.bar(
            sleep_behavior,
            x="SleepCategory",
            y="AvgCalories",
            title="Average Calories by Sleep Category",
            text_auto=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# =========================================================
# TAB 4 - WEIGHT & BMI
# =========================================================

with tab4:

    st.header("⚖️ Weight & BMI Analysis")

    weight_kpi_query = """
    SELECT
        COUNT(DISTINCT Id) AS Users,
        ROUND(AVG(WeightKg), 2) AS AvgWeightKg,
        ROUND(AVG(BMI), 2) AS AvgBMI
    FROM weight_data;
    """

    weight_kpi = run_query(weight_kpi_query)

    if not weight_kpi.empty:

        row = weight_kpi.iloc[0]

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "👥 Users",
            f"{int(row['Users']):,}"
        )

        c2.metric(
            "⚖️ Avg Weight",
            f"{row['AvgWeightKg']:.2f} kg"
        )

        c3.metric(
            "📏 Avg BMI",
            f"{row['AvgBMI']:.2f}"
        )

    col1, col2 = st.columns(2)

    # ---------- WEIGHT TREND ----------
    with col1:

        weight_trend_query = """
        SELECT
            DATE(
                STR_TO_DATE(
                    Date,
                    '%%c/%%e/%%Y %%r'
                )
            ) AS WeightDate,
            ROUND(AVG(WeightKg), 2) AS AvgWeight
        FROM weight_data
        WHERE WeightKg IS NOT NULL
        AND Date IS NOT NULL
        GROUP BY
            DATE(
                STR_TO_DATE(
                    Date,
                    '%%c/%%e/%%Y %%r'
                )
            )
        ORDER BY WeightDate
        """

        weight_trend_df = run_query(weight_trend_query)

        if not weight_trend_df.empty:

            fig = px.line(
            weight_trend_df,
            x="WeightDate",
            y="AvgWeight",
            markers=True,
            title="Average Weight Trend"
        )


            st.plotly_chart(
                fig,
                use_container_width=True
            )

    # ---------- BMI DISTRIBUTION ----------
    with col2:

        query = """
        SELECT
            BMICategory,
            COUNT(*) AS Records
        FROM weight_clean
        WHERE BMICategory <> 'Unknown'
        GROUP BY BMICategory
        ORDER BY Records DESC;
        """

        bmi = run_query(query)

        if not bmi.empty:

            fig = px.pie(
                bmi,
                names="BMICategory",
                values="Records",
                hole=0.45,
                title="BMI Category Distribution"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    st.caption(
        "BMI categories are descriptive groupings of the dataset "
        "and should not be interpreted as an individual medical diagnosis."
    )

# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.subheader("💡 Business Recommendations")

st.markdown(
    """
    **1. Personalized activity goals**  
    Use activity-level segmentation to tailor daily or weekly
    goals to different user behavior patterns.

    **2. Encourage movement**  
    Users with higher sedentary time can be targeted with
    reminders, movement prompts and activity challenges.

    **3. Promote sleep tracking**  
    Integrate sleep metrics into the overall wellness experience
    so users can view activity and sleep together.

    **4. Gamification**  
    Consider step challenges, streaks, milestones and achievement
    badges to support continued engagement.

    **5. Integrated wellness dashboard**  
    Combine activity, sleep and weight tracking into one
    personalized wellness view.
    """
)

st.caption(
    "Fitness & Wellness Analytics | SQL + Pandas + Streamlit"
)
