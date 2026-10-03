import json
import statistics
import requests
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

API_URL = "http://localhost:8000"
COHORT_FILE = "scripts/cohorts.json"

def run_evaluation():
    with open(COHORT_FILE, "r") as f:
        cohorts = json.load(f)

    results = {}

    print("\n" + "=" * 65)
    print("      DEFI CREDIT SCORING — EMPIRICAL COHORT EVALUATION")
    print("=" * 65)

    for cohort_name, wallets in cohorts.items():
        print(f"\n[Evaluating Cohort: {cohort_name.upper()}] ({len(wallets)} wallets)")
        results[cohort_name] = []

        for item in wallets:
            addr = item["address"]
            label = item["label"]
            try:
                res = requests.get(f"{API_URL}/score/{addr}", timeout=30)
                if res.status_code == 200:
                    data = res.json()
                    score = data["score"]
                    results[cohort_name].append(score)
                    print(f"  • {addr[:10]}... | Score: {score} | ({label})")
                else:
                    print(f"  • {addr[:10]}... | Failed (Status {res.status_code})")
            except Exception as e:
                print(f"  • {addr[:10]}... | Connection Error: {e}")

    # Summary Statistics
    print("\n" + "=" * 65)
    print("                 RESEARCH EVALUATION SUMMARY")
    print("=" * 65)
    print(f"{'Cohort':<25} {'Count':<8} {'Mean':<10} {'Median':<10} {'Min-Max':<12}")
    print("-" * 65)

    chart_data = []
    
    for cohort_name, scores in results.items():
        if scores:
            mean_sc = round(statistics.mean(scores), 1)
            med_sc = round(statistics.median(scores), 1)
            min_max = f"{min(scores)}-{max(scores)}"
            print(f"{cohort_name:<25} {len(scores):<8} {mean_sc:<10} {med_sc:<10} {min_max:<12}")
            
            # Prepare data for plotting
            clean_name = cohort_name.replace("_", " ").title()
            for s in scores:
                chart_data.append({"Cohort": clean_name, "Credit Score": s})
        else:
            print(f"{cohort_name:<25} 0        N/A        N/A        N/A")

    # Generate Academic Visualization
    if chart_data:
        print("\nGenerating evaluation charts...")
        df = pd.DataFrame(chart_data)
        
        plt.figure(figsize=(10, 6))
        sns.set_theme(style="whitegrid")
        
        # Create a Boxplot overlaid with individual data points (stripplot)
        ax = sns.boxplot(x="Cohort", y="Credit Score", data=df, palette="Set2", showfliers=False)
        sns.stripplot(x="Cohort", y="Credit Score", data=df, color=".25", size=8, jitter=True, alpha=0.7)
        
        plt.title("DeFi Credit Score Distribution by Borrower Cohort", fontsize=14, pad=15)
        plt.ylim(250, 850)
        plt.ylabel("Risk-Adjusted Score (300-850)", fontsize=12)
        plt.xlabel("Evaluation Cohort", fontsize=12)
        
        # Save the figure to the project root
        chart_filename = "score_distribution_chart.png"
        plt.savefig(chart_filename, dpi=300, bbox_inches="tight")
        print(f"Success! Academic chart saved to: {chart_filename}")

    print("=" * 65 + "\n")

if __name__ == "__main__":
    run_evaluation()