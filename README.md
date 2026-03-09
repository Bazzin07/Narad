# Narad - Intelligent News Aggregator and Analytics Platform

A robust, multilingual news aggregation and deep-analysis platform engineered to track, summarize, and cross-examine news articles across regions and sources. Narad provides insights into global and regional news coverage by leveraging modern Natural Language Processing (NLP) techniques and generative artificial intelligence.

## Features

- **Global and Regional Ingestion:** Continuous streaming and aggregation of multilingual news feeds covering major global sources and deeply regional Indian publications (English, Hindi, Telugu, Malayalam, Urdu, and more).
- **Real-Time Command Center:** A dedicated dashboard for tracking streaming news channels and aggregated regional coverage with synchronized live video feeds.
- **Geographic Filtering and Classification:** Algorithms that automatically separate and maintain scope clarity between domestic news and true international events.
- **Automatic Entity Extraction:** Background processing pipelines parse incoming articles to identify key locations, persons, and organizations using efficient localized NLP models.
- **Generative AI Analysis Suite:**
  - **Deep Dive and Fact Sheets:** Distill extensive articles into concise, structured bullet points containing only verified facts.
  - **Bias Analysis and Comparison:** Evaluate multiple coverage angles on the same story to highlight divergent biases or omitted perspectives.
  - **Event Timeline Generation:** Automatically construct chronological sequences of events across related developing stories.
  - **Explore Connections:** Discover latent interconnections between seemingly unrelated news events.
  - **Probe:** Structured conversational deep-diving that prompts precise lines of questioning regarding the article content.
- **Contextual Assistant (Ask Narad):** Conversational AI interface that queries the aggregated news database to answer user questions using synthesized grounding from raw articles.
- **Continuous Background Ingestion:** Automated scheduling incrementally pulls news feeds asynchronously, preventing performance degradation on serving APIs.

## Architecture and Technology Stack

Narad is built as a highly decoupled modern application relying on a scalable cloud-native infrastructure setup.

### Frontend
- **Framework:** Next.js (React) leveraging server-side rendering and static site generation.
- **Styling:** Tailwind CSS for a fully responsive, structured design system.
- **UI Components:** Interactive map displays, markdown parsers for AI streaming, and dynamic media embeds natively integrated.

### Backend APIs and Services
- **Framework:** FastAPI (Python 3.11) ensuring high-performance asynchronous request handling.
- **NLP Processing:** Local `spaCy` models for efficient, localized, multilingual Named Entity Recognition (NER). This approach strictly isolates logic from external NLP APIs to decrease vendor lock-in and latency.
- **Embeddings and Semantic Search:** Local generic sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`) integrated with FAISS indexing for rapid article clustering, deduplication, and document similarity operations.
- **Background Scheduling:** APScheduler framework for robust, non-blocking asynchronous intervals.

### AWS Cloud Infrastructure

The entire production ecosystem runs on Amazon Web Services (AWS) using managed resources and serverless models:

- **AWS App Runner:** Fully managed serverless container service running the FastAPI Dockerized backend. It is provisioned with `linux/amd64` images to scale seamlessly based on incoming API request pressure.
- **AWS Amplify:** Hosting and continuous delivery for the Next.js frontend application, delivering edge routing and optimized asset delivery worldwide.
- **Amazon RDS (PostgreSQL):** The primary, highly available relational storage engine maintaining article metadata, temporal logs, sources, and cached AI inferences.
- **Amazon Bedrock:** Foundational LLM integration utilizing secure cloud models (e.g., Amazon Titan and Claude) to power the generative features and conversational bots without managing dedicated inference GPU instances.
- **Amazon ECR:** Elastic Container Registry providing secure container image storage, serving as the artifact repository directly linked with the App Runner backend updates.
- **Amazon S3:** Object storage implementation responsible for reliably persisting extensive raw scraped articles and static analysis artifacts.

## Local Development Initialization

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL
- Active AWS Credentials explicitly authorized for Amazon Bedrock and Amazon S3.

### Backend Setup
1. Navigate to the `backend` directory.
2. Initialize and activate a Python virtual environment.
3. Install dependencies: `pip install -r requirements.txt`.
4. Procure generic NLP models: 
   ```bash
   python -m spacy download en_core_web_sm
   python -m spacy download xx_ent_wiki_sm
   ```
5. Configure your local `.env` with backend configuration, database URLs, and AWS regions.
6. Initialize the server: `uvicorn app.main:app --reload`.

### Frontend Setup
1. Navigate to the `frontend` directory.
2. Install dependencies: `npm install`.
3. Provide the frontend `.env.local` containing the backend API URI (`NEXT_PUBLIC_API_URL`).
4. Initialize the server: `npm run dev`.
