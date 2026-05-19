# 📊 Campaign Intelligence & Reporting Agent

An end-to-end, agentic data pipeline that ingests raw marketing campaign analytics, aggregates performance metrics, leverages an LLM for deep qualitative analysis, and automatically generates executive-ready PDF and HTML reports.

## 🚀 Overview

Marketing data is often deeply nested and difficult to interpret at scale. This project automates the entire reporting workflow:
1. **Extraction & Normalization:** Parses complex, nested JSON campaign and journey data (e.g., CleverTap exports).
2. **Aggregation:** Uses Pandas to calculate key metrics like Click-Through Rate (CTR) and Error Rates across different channels and regions.
3. **Agentic Analysis:** Feeds structured summaries into an OpenAI LLM using a strict prompt to generate quantitative scorecards, qualitative deep dives, and actionable recommendations.
4. **Automated Publishing:** Maps the LLM's structured JSON output into an HTML template and compiles a polished PDF deliverable.

## 🛠️ Tech Stack

* **Data Processing:** Python, Pandas, NumPy
* **AI & Analysis:** OpenAI API (`gpt-4o`)
* **Report Generation:** WeasyPrint (HTML to PDF)
* **Environment Management:** `python-dotenv`

## 🗂️ Architecture

The pipeline is separated into four distinct modules for clean separation of concerns:

* `campaign_pipeline.py` **(The Extractor):** Ingests `campaign_details.json`, gracefully handling missing stats, flattening nested dictionaries, and exporting normalized row-level metrics.
* `summary_generator.py` **(The Aggregator):** Merges channel metrics, calculates overall campaign/journey performance (CTR, error rates), and exports a unified `summary_data.json`.
* `llm_generate_blocks.py` **(The Brain):** Prompts the LLM with the summarized data to evaluate dimensions like *Personalization*, *Segmentation Depth*, and *Experimentation*. Outputs a strictly formatted `llm_output.json`.
* `report_generator.py` **(The Presenter):** Injects the LLM's JSON blocks into `template.html` and uses WeasyPrint to output `report.pdf`.

## ⚙️ Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/your-username/campaign-reporting-agent.git](https://github.com/your-username/campaign-reporting-agent.git)
   cd campaign-reporting-agent
