# Enterprise Marketing Intelligence Platform (MISP)

A decoupled, 3-tier business intelligence and data analytics platform designed to aggregate, process, and visualize cross-channel marketing campaign performance. 

## 🏗️ Architecture Overview
- **Database Layer**: PostgreSQL database housing raw campaign configurations and daily performance tracking metrics.
- **Backend API Layer (FastAPI)**: A robust REST API serving as a secure gateway, executing optimized analytical queries (handling missing data via `COALESCE`) and exposing 6 data routes.
- **Frontend Layer (Streamlit)**: An interactive, fully decoupled business intelligence dashboard that communicates exclusively with the backend via HTTP web requests.

## 🚀 How to Run the Platform

### 1. Prerequisites
Ensure you have Python 3.10+ installed and a running PostgreSQL instance with the `misp_db` database loaded.

### 2. Install Dependencies
```bash
pip install fastapi uvicorn streamlit pandas sqlalchemy psycopg2 requests plotly