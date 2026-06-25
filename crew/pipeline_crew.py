import litellm
from litellm import completion as original_completion

def patched_completion(*args, **kwargs):
    messages = kwargs.get("messages", [])
    for msg in messages:
        if isinstance(msg, dict) and "cache_breakpoint" in msg:
            del msg["cache_breakpoint"]
    return original_completion(*args, **kwargs)

litellm.completion = patched_completion

import os
from dotenv import load_dotenv
import duckdb

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

from crewai import Agent, Task, Crew, LLM

DB_PATH = "db/olist.duckdb"

def query(sql):
    conn = duckdb.connect(DB_PATH)
    result = conn.execute(sql).df()
    conn.close()
    return result.to_string()

def get_kpis():
    return {
        "top_categories": query("""
            SELECT product_category_name_english,
                   category_total_orders,
                   ROUND(category_avg_price, 2) as avg_price,
                   ROUND(category_avg_review, 2) as avg_review,
                   ROUND(category_late_rate * 100, 1) as late_pct
            FROM category_features
            ORDER BY category_total_orders DESC
            LIMIT 10
        """),
        "late_states": query("""
            SELECT customer_state, state_total_orders,
                   ROUND(state_late_rate * 100, 1) as late_pct,
                   ROUND(state_avg_payment, 2) as avg_payment
            FROM customer_features
            ORDER BY state_late_rate DESC
            LIMIT 10
        """),
        "seller_summary": query("""
            SELECT ROUND(AVG(seller_avg_review), 2) as platform_avg_review,
                   ROUND(AVG(seller_late_rate) * 100, 1) as platform_late_pct,
                   COUNT(*) as total_sellers,
                   SUM(seller_total_orders) as total_orders
            FROM seller_features
        """),
        "bad_sellers": query("""
            SELECT seller_id, seller_state,
                   ROUND(seller_avg_review, 2) as avg_review,
                   ROUND(seller_late_rate * 100, 1) as late_pct,
                   seller_total_orders
            FROM seller_features
            WHERE seller_total_orders >= 10
            ORDER BY seller_late_rate DESC
            LIMIT 10
        """),
    }

def run_crew():
    llm = LLM(
        model="openai/llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY")
    )

    kpis = get_kpis()

    analyst = Agent(
        role="Senior Business Analyst",
        goal="Analyze e-commerce KPIs and extract actionable business insights",
        backstory="Expert in e-commerce analytics with deep knowledge of marketplace dynamics.",
        llm=llm,
        verbose=False
    )

    anomaly_agent = Agent(
        role="Anomaly Detection Specialist",
        goal="Identify underperforming sellers, problematic categories, and delivery issues",
        backstory="Data scientist specializing in outlier detection and operational risk in e-commerce.",
        llm=llm,
        verbose=False
    )

    reporter = Agent(
        role="Business Report Writer",
        goal="Compile analytical findings into a clear executive markdown report",
        backstory="Business writer who turns raw data insights into compelling executive summaries.",
        llm=llm,
        verbose=False
    )

    analysis_task = Task(
        description=f"""
        Analyze the following Olist e-commerce KPI data and provide 5 key business insights:

        PLATFORM SUMMARY:
        {kpis['seller_summary']}

        TOP CATEGORIES BY VOLUME:
        {kpis['top_categories']}

        LATE DELIVERY BY STATE:
        {kpis['late_states']}

        Focus on: revenue opportunities, customer satisfaction trends, geographic patterns.
        """,
        expected_output="5 numbered business insights with data-backed reasoning.",
        agent=analyst
    )

    anomaly_task = Task(
        description=f"""
        Identify anomalies and risks in the following Olist seller and delivery data:

        WORST SELLERS (min 10 orders):
        {kpis['bad_sellers']}

        LATE DELIVERY BY STATE:
        {kpis['late_states']}

        TOP CATEGORIES:
        {kpis['top_categories']}

        Flag: high late rates, low review scores, geographic delivery problems.
        Provide 3-5 specific anomalies with recommended actions.
        """,
        expected_output="3-5 flagged anomalies with recommended corrective actions.",
        agent=anomaly_agent
    )

    report_task = Task(
        description="""
        Using the business insights and anomaly findings from the previous tasks,
        write a professional executive report in markdown format.

        Structure:
        # Olist E-Commerce Analytics Report

        ## Executive Summary
        ## Key Business Insights
        ## Risk Flags & Anomalies
        ## Recommended Actions
        ## Conclusion

        Keep it concise, data-driven, and actionable.
        """,
        expected_output="Complete markdown executive report.",
        agent=reporter,
        context=[analysis_task, anomaly_task]
    )

    crew = Crew(
        agents=[analyst, anomaly_agent, reporter],
        tasks=[analysis_task, anomaly_task, report_task],
        verbose=False
    )

    result = crew.kickoff()

    os.makedirs("reports", exist_ok=True)
    with open("reports/olist_report.md", "w", encoding="utf-8") as f:
        f.write(str(result))

    print("Report saved to reports/olist_report.md")
    print("\n" + "="*50)
    print(str(result))

if __name__ == "__main__":
    run_crew()