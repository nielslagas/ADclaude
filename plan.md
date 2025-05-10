Project: AD-Rapport Generator AI - Complete Takenlijst (v1.3)

Gekozen Technologie Stack:

Backend: Python/FastAPI/Celery
Database: PostgreSQL met pgvector (Lokaal via Docker voor dev)
Broker: Redis (Lokaal via Docker voor dev)
AI: Google Gemini 2.5 Pro (API)
Frontend: Vue.js
Lokale Dev Setup: Volledig lokaal (Docker PostgreSQL/Redis/Backend, Native Vue Dev Server)
IDE: Project IDX of Lokaal (VS Code/PyCharm)
Versiebeheer: Git/GitHub
IaC: Terraform of Pulumi
Hosting (Prod): Cloud Platform (bv. GCP Cloud Run, AWS ECS, Azure)
Project Management (Doorlopend vanaf Fase 0):

[~] Project Backlog Beheren (taken prioriteren, verfijnen).
[~] Voortgang Monitoren & Rapporteren.
[ ] Risicoregister Bijhouden & Acties Monitoren.
[ ] Stakeholder Communicatie Onderhouden.
[~] Documentatie Bijwerken (technisch, gebruiker).
Fase 0: Fundering & Planning (± 1-2 weken)

[x] Task 0.1: Definieer & Finaliseer MVP Scope en Succescriteria.
[x] Task 0.2: Maak GitHub Repository aan (Private).
[x] Task 0.3: Zet lokale PostgreSQL DB op met pgvector extensie.
[x] Task 0.4: Schakel pgvector extensie in & Configureer HNSW Indexering in lokale PostgreSQL.
[x] Task 0.5: Start Lokale Redis Server via Docker: docker run -d --name redis-celery-mvp -p 6379:6379 redis:latest.
[x] Task 0.6 (Bijgewerkt): Bevestig Frontend Framework: Vue.js.
[ ] Task 0.7: Kies Cloud Hosting Platform voor latere deployment & Zet basis IaC (Terraform/Pulumi) op.
[x] Task 0.8: Zet Ontwikkelomgeving op (IDE, Docker, Node.js/npm/yarn).
[x] Task 0.9: Clone GitHub Repository.
[x] Task 0.10 (Bijgewerkt): Initialiseer Backend (FastAPI) en Frontend (Vue.js via npm create vue@latest) projectstructuren in repo.
[x] Task 0.11 (Bijgewerkt): Installeer Core Dependencies (Backend: requirements.txt, Frontend: package.json voor Vue.js).
[x] Task 0.12: Configureer Basis .env / Secrets Management (voor API keys, lokale DB connectie, Lokale Redis URL).
[x] Task 0.13: Maak Dockerfile voor de FastAPI applicatie.
[x] Task 0.14: Maak Dockerfile voor de Celery worker.
[x] Task 0.15: Maak docker-compose.yml bestand voor lokale ontwikkeling (services: postgresql, redis, backend-api, backend-worker).
[x] Task 0.16: Zet Basis Celery Configuratie op in Python code (met Redis service naam).
[ ] Task 0.17: Stel Initiële Risicoregister op.
[ ] Task 0.18: Start Formele DPIA: Data mapping, identificeren risico's.
[ ] Task 0.19: Vraag DPA's op bij Google Cloud voor Gemini API.
Fase 1: MVP Backend Kern (± 2-3 weken)

Backend code draait lokaal via docker-compose up, verbindt met lokale PostgreSQL.
[x] Task 1.1: Implementeer authenticatie in FastAPI (JWT middleware).
[x] Task 1.2: Definieer DB Modellen (MVP Scope) met SQLModel/SQLAlchemy.
[x] Task 1.3: Zet PostgreSQL connectie op met SQLAlchemy.
[x] Task 1.4: Sla structuur van één template op (JSON Schema in DB).
[x] Task 1.5: Implementeer API Endpoints: Case CRUD (/cases), Document Lijst (/cases/{case_id}/documents).
[x] Task 1.6: Implementeer API Endpoint: Document Upload (/cases/{case_id}/upload_mvp) (docx/txt, lokale Storage, DB record, trigger Celery).
[x] Task 1.7: Implementeer Celery Taak Stubs. Update status in DB.
[x] Task 1.8: Implementeer Basis Logging voor backend.
[x] Task 1.9: Implementeer verbeterde foutafhandeling en diagnostische tools voor backend API endpoints.
[ ] Task 1.10: Schrijf Unit & Integratie Tests voor API's en DB Models.
Fase 2: MVP Basis RAG & Generatie (± 3-4 weken, Iteratief)

Celery taken draaien in Docker, interacteren met lokale PostgreSQL/pgvector.
[x] Task 2.1: Implementeer process_document_mvp taak (basis parsing docx/txt).
[x] Task 2.2: Implementeer basis document chunking (zonder embeddings voor MVP).
[~] Task 2.3: Implementeer optionele embedding generatie met Google API voor chunks.
[~] Task 2.4: Implementeer generate_report_mvp taak: - In progress
Voor essentiële MVP secties:
Basis vraag formuleren.
Vector similarity search (pgvector) of alternatieve tekst zoekfunctie.
Ontwikkel/Test/Verfijn Prompt (Grounding, basis Markdown output).
Roep Gemini 1.5 Pro API aan.
Log gebruikte chunks.
Assembleer & Sla output op. Update status.
[ ] Task 2.5: Handmatige Evaluatie & Prompt Iteratie.
[ ] Task 2.6: Breid Unit/Integratie Tests uit.
Fase 3: MVP Frontend & Integratie (± 3-4 weken, Parallel)

[x] Task 3.1: Zet Vue.js project verder op (routing met Vue Router, state management met Pinia).
[x] Task 3.2: Start frontend lokaal met npm run dev (Vue.js dev server).
[x] Task 3.3: Implementeer Login/Registratie UI in Vue (met mock authenticatie voor lokale ontwikkeling).
[x] Task 3.4: Implementeer Case Management UI (Vue components).
[x] Task 3.5: Implementeer Document Upload UI (Vue component).
[x] Task 3.6: Implementeer Status Weergave in Vue (polling/refresh).
[x] Task 3.7: Implementeer Rapport Generatie Knop in Vue.
[x] Task 3.8: Implementeer verbeterde foutafhandeling in Vue.js componenten met gebruiksvriendelijke berichten.
[x] Task 3.9: Implementeer diagnostische tools voor API calls en authenticatie (TestView.vue).
[x] Task 3.10: Implementeer Frontend Routing (Vue Router) & Auth Guarding.
[x] Task 3.11: Koppel Vue UI aan Backend API Endpoints (via fetch).
[ ] Task 3.12: Implementeer Simpele Rapport Viewer in Vue (toont Markdown, <textarea>).
Fase 4: MVP Testen, Feedback & Afronding (± 2 weken)

[~] Task 4.1: Voer End-to-End tests uit (Lokale Vue frontend praat met lokale Docker backend). - In progress
[x] Task 4.2: Implementeer basis database security (PostgreSQL ROW LEVEL SECURITY).
[~] Task 4.3: Voer handmatige security tests uit. - In progress
[x] Task 4.4: Verbeter geheugengebruik in document processing worker.
[x] Task 4.5: Verbeter JWT token verwerking met betere logging en foutafhandeling.
[ ] Task 4.6: User Acceptance Testing (UAT) met 1-2 experts. Verzamel feedback.
[ ] Task 4.7: Verwerk Kritieke MVP feedback / bugs.
[~] Task 4.8: Schrijf Beknopte MVP Documentatie (incl. setup). - In progress
[ ] Task 4.9: Bereid deployment voor & Deploy MVP naar Staging.
(Beslismoment: Evalueer MVP resultaten & feedback. Doorgaan?)

Fase 5: Geavanceerde Parsing & RAG (Iteratief, Post-MVP)

[ ] Task 5.1: Implementeer Structure-Aware Parsing library. Pas process_document taak aan.
[ ] Task 5.2: Implementeer & Evalueer Geavanceerde Chunking Strategieën.
[ ] Task 5.3: Implementeer Opslag van Rijke Metadata bij Chunks.
[ ] Task 5.4: Implementeer Hybrid Search (pgvector + FTS).
[ ] Task 5.5: Implementeer Reranking (bv. met cross-encoder).
[ ] Task 5.6: Implementeer evt. Query Transformation technieken.
[ ] Task 5.7: Ontwikkel RAG Evaluation Suite & Automatisering.
[ ] Task 5.8: Gebruik Eval Suite om RAG pipeline iteratief te verbeteren.
Fase 6: Uitgebreide AI & Features (Iteratief, Post-MVP)

[ ] Task 6.1: Implementeer Multi-Template Support (Backend & Frontend).
[ ] Task 6.2: Benchmark Gemini native OCR/ASR vs. Gespecialiseerde Tools.
[ ] Task 6.3: Implementeer Gekozen OCR oplossing (indien nodig).
[ ] Task 6.4: Implementeer Gekozen ASR oplossing (indien nodig).
[ ] Task 6.5 (Bijgewerkt): Verfijn Structured Output Prompting (JSON mode). Pas backend Pydantic validatie van AI output toe.
[ ] Task 6.6: Ontwikkel Prompt Library / Management Systeem.
[ ] Task 6.7: Verfijn Few-Shot Examples.
Fase 7: Volledige Frontend & UX (Post-MVP)

[ ] Task 7.1 (Bijgewerkt): Selecteer & Integreer Vue-compatibele Rich Text Editor.
[ ] Task 7.2 (Bijgewerkt): Selecteer & Integreer Vue-compatibele Diff Viewer.
[ ] Task 7.3 (Bijgewerkt): Implementeer Source Attribution UI in Vue.
[ ] Task 7.4: Onderzoek & Implementeer evt. Real-time Collaboration features in Vue.
[ ] Task 7.5: Implementeer Realtime Status Updates (Supabase Realtime in Vue).
[ ] Task 7.6: Verbeter Algemene UI/UX flow in Vue (o.b.v. HCAI & feedback).
[ ] Task 7.7: Implementeer Feedback mechanisme in UI.
Fase 8: Compliance, Security & Schaalbaarheid (Post-MVP)

[ ] Task 8.1: Finaliseer & Documenteer DPIA; implementeer mitigaties.
[ ] Task 8.2: Finaliseer & Teken DPA's.
[ ] Task 8.3: Implementeer & Test Volledige RLS policies grondig.
[ ] Task 8.4: Voer Uitgebreide Security Tests uit (SAST, DAST, evt. Pentest).
[ ] Task 8.5: Onderzoek & Implementeer evt. Pseudonimisering strategie.
[ ] Task 8.6: Zet Bias Monitoring op.
[ ] Task 8.7: Voer Performance & Load Tests uit. Optimaliseer.
[ ] Task 8.8: Configureer Auto-scaling voor backend/workers.
[ ] Task 8.9: Verfijn Logging & Monitoring voor productie.
Fase 9: Productie Deployment & Lancering (Post-MVP)

[ ] Task 9.1: Zet Volledige CI/CD Pipeline op (Testen, Scans, IaC, Deploy).
[ ] Task 9.2: Configureer Productie Hosting Omgeving (Cloud, Supabase Prod, Redis Prod).
[ ] Task 9.3: Ontwikkel Gebruikerstraining Materiaal & Documentatie.
[ ] Task 9.4: Ontwikkel & Voer Gebruikersadoptie & Communicatieplan uit.
[ ] Task 9.5: Voer Finale UAT uit op staging.
[ ] Task 9.6: Deploy naar Productie.
[ ] Task 9.7: Voer Initiële User Onboarding & Training uit.
Fase 10: Continue Verbetering & Onderhoud (Doorlopend)

[ ] Task 10.1: Monitor Applicatie Performance, Errors & Kosten.
[ ] Task 10.2: Verzamel & Analyseer Gebruikersfeedback.
[ ] Task 10.3: Beheer Product Backlog.
[ ] Task 10.4: Plan & Voer Regelmatige Sprints/Iteraties uit.
[ ] Task 10.5: Onderhoud & Update Dependencies (Python, Vue, etc.).
[ ] Task 10.6: Update AI Model / Prompts / RAG pipeline.
[ ] Task 10.7: Bied Gebruikersondersteuning & Bug Fixing.
[ ] Task 10.8: Periodieke Security & Compliance Reviews.