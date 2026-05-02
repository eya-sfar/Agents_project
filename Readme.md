# 🔭 Intelligent University Observatory
## Research & Lab Management System — Multi-Agent Architecture

---

## 📁 Project Structure

```
university_observatory/
├── agents/                        # All MAS agents
│   ├── __init__.py
│   ├── agent_coordinator.py       # Orchestrates all agents
│   ├── agent_researcher_scraper.py
│   ├── agent_publication_scraper.py
│   ├── agent_lab_scraper.py
│   ├── agent_cluster.py           # K-Means / DBSCAN clustering
│   ├── agent_expertise_matcher.py
│   ├── agent_collab_advisor.py
│   ├── agent_negotiator.py        # Game-theory negotiation
│   └── agent_dashboard_interface.py
│
├── database/
│   ├── __init__.py
│   ├── models.py                  # SQLAlchemy ORM models
│   ├── connection.py              # PostgreSQL connection pool
│   ├── migrations/
│   │   └── init_schema.sql        # Full DB schema
│   └── repositories/
│       ├── researcher_repo.py
│       ├── lab_repo.py
│       ├── publication_repo.py
│       └── cluster_repo.py
│
├── api/
│   ├── __init__.py
│   ├── app.py                     # Flask app factory
│   └── routes/
│       ├── researchers.py
│       ├── labs.py
│       ├── publications.py
│       ├── clusters.py
│       └── agents.py
│
├── dashboard/
│   ├── app.py                     # Streamlit dashboard
│   └── static/
│       ├── css/style.css
│       └── js/charts.js
│
├── config/
│   ├── __init__.py
│   └── settings.py                # All configuration
│
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   └── helpers.py
│
├── tests/
│   ├── test_agents.py
│   └── test_api.py
│
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── run_agents.py                  # Entry point for MAS
└── run_api.py                     # Entry point for Flask API
```

---

## 🚀 Quick Start

### 1. Clone & install
```bash
git clone <repo>
cd university_observatory
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Setup PostgreSQL
```bash
# Using Docker (recommended)
docker-compose up -d postgres

# Or manually create a database
psql -U postgres -c "CREATE DATABASE university_obs;"
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 4. Initialize the database
```bash
python -c "from database.connection import init_db; init_db()"
```

### 5. Run the MAS agents
```bash
python run_agents.py
```

### 6. Run the Flask API
```bash
python run_api.py
```

### 7. Run the Streamlit Dashboard
```bash
streamlit run dashboard/app.py
```

---

## 🤖 Agent Descriptions

| Agent | Role |
|-------|------|
| `AgentCoordinator` | Orchestrates all agents, manages workflow |
| `AgentResearcherScraper` | Scrapes researcher profiles (Google Scholar, DBLP) |
| `AgentPublicationScraper` | Collects publications metadata |
| `AgentLabScraper` | Scrapes laboratory info |
| `AgentCluster` | Clusters researchers by expertise (K-Means) |
| `AgentExpertiseMatcher` | Matches researchers by complementary expertise |
| `AgentCollabAdvisor` | Recommends collaboration pairs |
| `AgentNegotiator` | Game-theory based negotiation simulation |
| `AgentDashboardInterface` | Pushes live data to dashboard |

---

## 🧰 Tech Stack
- **MAS**: Mesa + custom agent base
- **Database**: PostgreSQL + SQLAlchemy
- **API**: Flask + Flask-RESTX
- **Dashboard**: Streamlit + Plotly
- **ML**: scikit-learn (TF-IDF, K-Means, cosine similarity)
- **Scraping**: BeautifulSoup, Requests, scholarly