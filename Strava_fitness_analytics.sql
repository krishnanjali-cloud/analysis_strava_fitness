-- STRAVA FITNESS DATA ANALYTICS
-- MySQL SQL analysis and insight queries
-- Source tables:
--   daily_activity
--   sleep_data
--   weight_data

CREATE DATABASE IF NOT EXISTS fitness_analytics;
USE fitness_analytics;

-- =========================================================
-- 1. TABLES
-- =========================================================

DROP TABLE IF EXISTS daily_activity;
CREATE TABLE daily_activity (
    Id BIGINT,
    ActivityDate DATE,
    TotalSteps INT,
    TotalDistance DECIMAL(10,2),
    TrackerDistance DECIMAL(10,2),
    LoggedActivitiesDistance DECIMAL(10,2),
    VeryActiveDistance DECIMAL(10,2),
    ModeratelyActiveDistance DECIMAL(10,2),
    LightActiveDistance DECIMAL(10,2),
    SedentaryActiveDistance DECIMAL(10,2),
    VeryActiveMinutes INT,
    FairlyActiveMinutes INT,
    LightlyActiveMinutes INT,
    SedentaryMinutes INT,
    Calories INT
);

DROP TABLE IF EXISTS sleep_data;
CREATE TABLE sleep_data (
    Id BIGINT,
    SleepDay DATETIME,
    TotalSleepRecords INT,
    TotalMinutesAsleep INT,
    TotalTimeInBed INT
);

DROP TABLE IF EXISTS weight_data;
CREATE TABLE weight_data (
    Id BIGINT,
    Date DATETIME,
    WeightKg DECIMAL(10,2),
    WeightPounds DECIMAL(10,2),
    Fat DECIMAL(10,2),
    BMI DECIMAL(10,2),
    IsManualReport BOOLEAN,
    LogId BIGINT
);

-- =========================================================
-- 2. DATA QUALITY CHECKS
-- =========================================================

-- Record counts
SELECT 'daily_activity' AS table_name, COUNT(*) AS records FROM daily_activity
UNION ALL
SELECT 'sleep_data', COUNT(*) FROM sleep_data
UNION ALL
SELECT 'weight_data', COUNT(*) FROM weight_data;

-- Duplicate activity records
SELECT Id, ActivityDate, COUNT(*) AS duplicate_count
FROM daily_activity
GROUP BY Id, ActivityDate
HAVING COUNT(*) > 1;

-- Duplicate sleep records
SELECT Id, SleepDay, COUNT(*) AS duplicate_count
FROM sleep_data
GROUP BY Id, SleepDay
HAVING COUNT(*) > 1;

-- Duplicate weight records
SELECT Id, Date, COUNT(*) AS duplicate_count
FROM weight_data
GROUP BY Id, Date
HAVING COUNT(*) > 1;

-- NULL checks: activity
SELECT
    SUM(Id IS NULL) AS null_id,
    SUM(ActivityDate IS NULL) AS null_date,
    SUM(TotalSteps IS NULL) AS null_steps,
    SUM(TotalDistance IS NULL) AS null_distance,
    SUM(Calories IS NULL) AS null_calories
FROM daily_activity;

-- NULL checks: sleep
SELECT
    SUM(Id IS NULL) AS null_id,
    SUM(SleepDay IS NULL) AS null_sleep_day,
    SUM(TotalMinutesAsleep IS NULL) AS null_sleep_minutes,
    SUM(TotalTimeInBed IS NULL) AS null_bed_minutes
FROM sleep_data;

-- NULL checks: weight
SELECT
    SUM(Id IS NULL) AS null_id,
    SUM(Date IS NULL) AS null_date,
    SUM(WeightKg IS NULL) AS null_weight,
    SUM(BMI IS NULL) AS null_bmi
FROM weight_data;

-- =========================================================
-- 3. CLEAN / DERIVED VIEWS
-- =========================================================

DROP VIEW IF EXISTS activity_clean;
CREATE VIEW activity_clean AS
SELECT
    Id,
    ActivityDate,
    DAYNAME(ActivityDate) AS DayName,
    DAYOFWEEK(ActivityDate) AS DayNumber,
    TotalSteps,
    TotalDistance,
    TrackerDistance,
    LoggedActivitiesDistance,
    VeryActiveDistance,
    ModeratelyActiveDistance,
    LightActiveDistance,
    SedentaryActiveDistance,
    VeryActiveMinutes,
    FairlyActiveMinutes,
    LightlyActiveMinutes,
    SedentaryMinutes,
    Calories,
    (
        VeryActiveMinutes +
        FairlyActiveMinutes +
        LightlyActiveMinutes
    ) AS ActiveMinutes,
    (
        VeryActiveMinutes +
        FairlyActiveMinutes
    ) AS ModerateVigorousMinutes
FROM daily_activity;

DROP VIEW IF EXISTS activity_classification;
CREATE VIEW activity_classification AS
SELECT
    *,
    CASE
        WHEN TotalSteps < 5000 THEN 'Sedentary'
        WHEN TotalSteps < 7500 THEN 'Low Active'
        WHEN TotalSteps < 10000 THEN 'Moderately Active'
        ELSE 'Highly Active'
    END AS ActivityLevel
FROM activity_clean;

DROP VIEW IF EXISTS sleep_clean;
CREATE VIEW sleep_clean AS
SELECT
    Id,
    DATE(SleepDay) AS SleepDate,
    TotalSleepRecords,
    TotalMinutesAsleep,
    TotalTimeInBed,
    ROUND(TotalMinutesAsleep / 60, 2) AS SleepHours,
    ROUND(
        TotalMinutesAsleep / NULLIF(TotalTimeInBed, 0) * 100,
        2
    ) AS SleepEfficiency
FROM sleep_data;

DROP VIEW IF EXISTS weight_clean;
CREATE VIEW weight_clean AS
SELECT
    Id,
    Date AS WeightDate,
    WeightKg,
    WeightPounds,
    Fat,
    BMI,
    IsManualReport,
    LogId,
    CASE
        WHEN BMI IS NULL THEN 'Unknown'
        WHEN BMI < 18.5 THEN 'Underweight'
        WHEN BMI < 25 THEN 'Normal'
        WHEN BMI < 30 THEN 'Overweight'
        ELSE 'Obesity'
    END AS BMICategory
FROM weight_data;

-- =========================================================
-- 4. OVERALL ACTIVITY INSIGHTS
-- =========================================================

SELECT
    COUNT(*) AS total_activity_records,
    COUNT(DISTINCT Id) AS total_users,
    ROUND(AVG(TotalSteps), 0) AS avg_steps,
    ROUND(AVG(TotalDistance), 2) AS avg_distance,
    ROUND(AVG(Calories), 0) AS avg_calories
FROM daily_activity;

-- User-level activity summary
SELECT
    Id,
    ROUND(AVG(TotalSteps), 0) AS AvgSteps,
    ROUND(AVG(TotalDistance), 2) AS AvgDistance,
    ROUND(AVG(Calories), 0) AS AvgCalories,
    ROUND(AVG(SedentaryMinutes), 0) AS AvgSedentaryMinutes
FROM daily_activity
GROUP BY Id
ORDER BY AvgSteps DESC;
select * from daily_activity;
describe daily_activity;

-- Activity by weekday
SELECT
    DayName,
    ROUND(AVG(TotalSteps), 0) AS AvgSteps,
    ROUND(AVG(TotalDistance), 2) AS AvgDistance,
    ROUND(AVG(Calories), 0) AS AvgCalories
FROM activity_clean
GROUP BY DayName, DayNumber
ORDER BY DayNumber;

-- Activity intensity
SELECT
    ActivityLevel,
    COUNT(*) AS Records,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS Percentage
FROM activity_classification
GROUP BY ActivityLevel
ORDER BY Records DESC;

-- Activity intensity minutes
SELECT
    ROUND(AVG(VeryActiveMinutes), 2) AS AvgVeryActiveMinutes,
    ROUND(AVG(FairlyActiveMinutes), 2) AS AvgFairlyActiveMinutes,
    ROUND(AVG(LightlyActiveMinutes), 2) AS AvgLightlyActiveMinutes,
    ROUND(AVG(SedentaryMinutes), 2) AS AvgSedentaryMinutes
FROM daily_activity;

-- Top 10 highest-step days
SELECT
    ActivityDate,
    Id,
    TotalSteps,
    TotalDistance,
    Calories
FROM daily_activity
ORDER BY TotalSteps DESC
LIMIT 10;

-- Top 10 calorie-burning days
SELECT
    ActivityDate,
    Id,
    TotalSteps,
    TotalDistance,
    Calories
FROM daily_activity
ORDER BY Calories DESC
LIMIT 10;

-- Monthly trend
SELECT
    DATE_FORMAT(ActivityDate, '%Y-%m') AS Month,
    ROUND(AVG(TotalSteps), 0) AS AvgSteps,
    ROUND(AVG(TotalDistance), 2) AS AvgDistance,
    ROUND(AVG(Calories), 0) AS AvgCalories
FROM daily_activity
GROUP BY Month
ORDER BY Month;

-- =========================================================
-- 5. SLEEP INSIGHTS
-- =========================================================

SELECT
    COUNT(DISTINCT Id) AS Users,
    ROUND(AVG(TotalMinutesAsleep) / 60, 2) AS AvgSleepHours,
    ROUND(AVG(TotalTimeInBed) / 60, 2) AS AvgTimeInBed,
    ROUND(AVG(TotalMinutesAsleep / NULLIF(TotalTimeInBed,0)) * 100, 2)
        AS AvgSleepEfficiency
FROM sleep_data;

-- Sleep category distribution
SELECT
    CASE
        WHEN TotalMinutesAsleep < 360 THEN 'Less than 6 hours'
        WHEN TotalMinutesAsleep < 420 THEN '6-7 hours'
        WHEN TotalMinutesAsleep < 480 THEN '7-8 hours'
        ELSE '8+ hours'
    END AS SleepCategory,
    COUNT(*) AS Records
FROM sleep_data
GROUP BY SleepCategory
ORDER BY Records DESC;

-- Sleep by weekday
SELECT
    DAYNAME(SleepDay) AS DayName,
    DAYOFWEEK(SleepDay) AS DayNumber,
    ROUND(AVG(TotalMinutesAsleep) / 60, 2) AS AvgSleepHours
FROM sleep_data
GROUP BY DayName, DayNumber
ORDER BY DayNumber;

-- =========================================================
-- 6. ACTIVITY + SLEEP COMBINED ANALYSIS
-- =========================================================

SELECT
    a.Id,
    a.ActivityDate,
    a.TotalSteps,
    a.TotalDistance,
    a.Calories,
    s.SleepHours,
    s.SleepEfficiency
FROM activity_clean a
JOIN sleep_clean s
    ON a.Id = s.Id
    AND a.ActivityDate = s.SleepDate;

-- Sleep versus activity dataset
SELECT
    a.TotalSteps,
    a.Calories,
    a.TotalDistance,
    s.SleepHours,
    s.SleepEfficiency
FROM activity_clean a
JOIN sleep_clean s
    ON a.Id = s.Id
    AND a.ActivityDate = s.SleepDate;

-- Average activity by sleep category
SELECT
    CASE
        WHEN s.SleepHours < 6 THEN 'Less than 6 hours'
        WHEN s.SleepHours < 7 THEN '6-7 hours'
        WHEN s.SleepHours < 8 THEN '7-8 hours'
        ELSE '8+ hours'
    END AS SleepCategory,
    ROUND(AVG(a.TotalSteps), 0) AS AvgSteps,
    ROUND(AVG(a.Calories), 0) AS AvgCalories,
    ROUND(AVG(a.TotalDistance), 2) AS AvgDistance
FROM activity_clean a
JOIN sleep_clean s
    ON a.Id = s.Id
    AND a.ActivityDate = s.SleepDate
GROUP BY SleepCategory
ORDER BY SleepCategory;

-- =========================================================
-- 7. WEIGHT / BMI INSIGHTS
-- =========================================================

SELECT
    COUNT(DISTINCT Id) AS Users,
    ROUND(AVG(WeightKg), 2) AS AvgWeightKg,
    ROUND(AVG(BMI), 2) AS AvgBMI
FROM weight_data;

-- BMI category distribution
SELECT
    BMICategory,
    COUNT(*) AS Records,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS Percentage
FROM weight_clean
WHERE BMICategory <> 'Unknown'
GROUP BY BMICategory
ORDER BY Records DESC;

-- Weight trend
SELECT
    DATE(WeightDate) AS WeightDate,
    ROUND(AVG(WeightKg), 2) AS AvgWeightKg,
    ROUND(AVG(BMI), 2) AS AvgBMI
FROM weight_clean
GROUP BY DATE(WeightDate)
ORDER BY WeightDate;

-- User weight summary
SELECT
    Id,
    MIN(WeightKg) AS MinWeightKg,
    MAX(WeightKg) AS MaxWeightKg,
    ROUND(AVG(WeightKg), 2) AS AvgWeightKg,
    MIN(WeightDate) AS FirstRecord,
    MAX(WeightDate) AS LastRecord
FROM weight_clean
GROUP BY Id
ORDER BY AvgWeightKg DESC;

-- =========================================================
-- 8. DASHBOARD-READY QUERIES
-- =========================================================

-- KPI query
SELECT
    COUNT(DISTINCT Id) AS Users,
    ROUND(AVG(TotalSteps), 0) AS AvgSteps,
    ROUND(AVG(TotalDistance), 2) AS AvgDistance,
    ROUND(AVG(Calories), 0) AS AvgCalories,
    ROUND(AVG(SedentaryMinutes), 0) AS AvgSedentaryMinutes
FROM daily_activity;

-- Activity weekday chart
SELECT
    DayName,
    DayNumber,
    ROUND(AVG(TotalSteps), 0) AS AvgSteps,
    ROUND(AVG(Calories), 0) AS AvgCalories,
    ROUND(AVG(TotalDistance), 2) AS AvgDistance
FROM activity_clean
GROUP BY DayName, DayNumber
ORDER BY DayNumber;

-- Activity level chart
SELECT
    ActivityLevel,
    COUNT(*) AS Records
FROM activity_classification
GROUP BY ActivityLevel
ORDER BY Records DESC;

-- Sleep chart
SELECT
    SleepCategory,
    Records
FROM (
    SELECT
        CASE
            WHEN TotalMinutesAsleep < 360 THEN 'Less than 6 hours'
            WHEN TotalMinutesAsleep < 420 THEN '6-7 hours'
            WHEN TotalMinutesAsleep < 480 THEN '7-8 hours'
            ELSE '8+ hours'
        END AS SleepCategory,
        COUNT(*) AS Records
    FROM sleep_data
    GROUP BY SleepCategory
) x;

-- Weight trend chart
SELECT
    DATE(WeightDate) AS WeightDate,
    ROUND(AVG(WeightKg), 2) AS AvgWeightKg
FROM weight_clean
GROUP BY DATE(WeightDate)
ORDER BY WeightDate;

-- BMI chart
SELECT
    BMICategory,
    COUNT(*) AS Records
FROM weight_clean
WHERE BMICategory <> 'Unknown'
GROUP BY BMICategory
ORDER BY Records DESC;

select * from daily_activity;
select * from sleep_data;
select * from weight_data;
show tables;
drop tables dailyactivity_merged,sleepday_merged,weightloginfo_merged;
