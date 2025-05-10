Projectvoorstel: AD-Rapport Generator AI (MVP)

Datum: 6 mei 2025
Versie: 1.0
Locatie: IJmuiden, Noord-Holland

1. Projecteigenaar:
[Naam van de initiatiefnemer/opdrachtgever]

2. Projectmanager:
[Naam van de projectmanager, of 'Nader te bepalen']

3. Inleiding & Achtergrond:
Het opstellen van arbeidsdeskundige (AD) rapportages is een essentieel, maar vaak tijdrovend proces voor arbeidsdeskundigen. Het verzamelen, analyseren en synthetiseren van informatie uit diverse bronnen (dossiers, FML, gespreksverslagen) naar een gestructureerd rapport vereist veel handmatig werk. Dit project beoogt dit proces te ondersteunen en te versnellen door gebruik te maken van moderne Artificiële Intelligentie (AI). Door een AI-model (Google Gemini 1.5 Pro) in te zetten middels Retrieval-Augmented Generation (RAG), kan op basis van geüploade documenten automatisch een concept-rapport gegenereerd worden volgens een specifiek format (zoals gebruikt door bv. Vector Advies of Staatvandienst). Dit stelt de arbeidsdeskundige in staat zich meer te focussen op analyse, beoordeling en de menselijke aspecten van het werk, terwijl de AI ondersteunt bij het routinematige schrijfwerk. Dit voorstel richt zich op de ontwikkeling van een Minimum Viable Product (MVP) om de kernfunctionaliteit te valideren.

4. Doelstellingen:

MVP Hoofddoel: Het opleveren van een functioneel Minimum Viable Product (MVP) van de AD-Rapport Generator applicatie binnen circa 10-11 weken (conform Fase 0-4 van het gedetailleerde plan). Dit MVP moet de technische haalbaarheid van de kern-pipeline (upload, analyse, generatie) aantonen en initiële feedback verzamelen van 1-2 testgebruikers (arbeidsdeskundigen).
MVP Specifieke Doelen:
Gebruikers kunnen authenticeren en een 'case' aanmaken.
Gebruikers kunnen documenten van type .docx en .txt uploaden per case.
De applicatie kan op verzoek een concept genereren voor essentiële secties (bv. Samenvatting, Belastbaarheid, Visie AD) van één vooraf gedefinieerd AD-rapport template.
De gegenereerde concepttekst is gebaseerd op de inhoud van de geüploade documenten via een basis RAG-proces.
Gebruikers kunnen de gegenereerde concepttekst inzien en kopiëren via een eenvoudige Vue.js webinterface.
Lange Termijn Visie: Een volwaardige, veilige en gebruiksvriendelijke webapplicatie die de efficiëntie en consistentie van AD-rapportages significant verbetert, ondersteuning biedt voor diverse templates en documenttypes (incl. audio/scans), en een naadloze review-workflow faciliteert, waarbij de expert altijd de volledige controle behoudt.
5. Scope (MVP):

Inclusief:
Backend ontwikkeling (Python/FastAPI/Celery) voor de MVP-functionaliteit.
Gebruik van Supabase (Cloud Instance) voor authenticatie, opslag (documenten), en database (PostgreSQL met pgvector).
Integratie met Google Gemini 2.5 Pro API voor basis RAG en tekstgeneratie.
Basis parsing van .docx en .txt.
Basis chunking, embedding en vector search.
Generatie van vooraf gedefinieerde kernsecties van één rapport template.
Eenvoudige web frontend (Vue.js) voor login, case aanmaken, upload, status weergave, generatie trigger, en output weergave/kopieëren.
Basis Row Level Security (RLS) implementatie in Supabase.
Initiële DPIA-documentatie.
Exclusief (voor MVP):
Ondersteuning audio/scans (ASR/OCR).
Geavanceerde RAG-technieken (hybrid search, reranking, etc.).
Structure-aware parsing en geavanceerde chunking.
Ondersteuning voor meerdere rapport templates of template beheer.
Geavanceerde frontend review-tools (rich text editor, diff viewer, source attribution UI).
Geautomatiseerde RAG-evaluatie en bias monitoring.
Volledige CI/CD pipeline en productie-deployment.
Uitgebreide gebruikersrollen en permissies.
6. Deliverables (MVP):

Een werkende MVP webapplicatie, toegankelijk voor testgebruikers (op staging omgeving).
Broncode van de backend en Vue.js frontend in een GitHub repository.
Beknopte technische documentatie en gebruikersinstructies voor de MVP.
Resultaten en feedback van de User Acceptance Test (UAT) door 1-2 experts.
Initiële documentatie voor de Data Protection Impact Assessment (DPIA).
7. Belanghebbenden:

Primair: Arbeidsdeskundigen (eindgebruikers).
Secundair: Projecteigenaar, Ontwikkelaar(s).
Indirect: Werkgevers/Werknemers (als subjecten in de rapporten), UWV, Re-integratiebedrijven.
8. Technologie & Aanpak:

Backend: Python, FastAPI, Celery, Redis.
BaaS: Supabase (Cloud Instance: PostgreSQL, pgvector, Auth, Storage).
AI: Google Gemini 1.5 Pro (via API).
Frontend: Vue.js.
Ontwikkelomgeving: Project IDX (of lokale IDE), GitHub.
Lokale Ontwikkeling: Hybride aanpak: gebruik van de beheerde Supabase cloud instance, met Redis en de Python backend (API/Worker) draaiend in Docker containers (via Docker Compose), en de Vue.js frontend via de Node.js development server.
Methodiek: Gefaseerde aanpak startend met MVP, iteratieve ontwikkeling (vooral AI-componenten), sterke focus op Human-in-the-Loop en AVG/GDPR-compliance.
9. Planning & Fasering (Globaal - MVP):
Het MVP wordt ontwikkeld in een periode van circa 10-11 weken, gericht op validatie en feedback, en omvat Fase 0 t/m 4 uit het gedetailleerde projectplan (Setup -> Backend Kern -> Basis RAG -> Frontend -> Testen & Afronding).

10. Risico's (Hoog Over):

AI Kwaliteit: Risico op onvoldoende nauwkeurigheid of hallucinaties in MVP-output. (Mitigatie: Grounding prompts, handmatige evaluatie).
AVG/GDPR: Verwerking van gevoelige persoonsgegevens brengt compliance-risico's mee. (Mitigatie: Start DPIA, basis RLS, DPA's in overweging).
Technische Complexiteit: RAG en asynchrone verwerking zijn complex. (Mitigatie: Starten met basis implementatie).
Gebruikersadoptie: Risico dat MVP (te) beperkt is voor validatie. (Mitigatie: Duidelijke communicatie MVP-scope, focus op potentieel).
Kosten: Onverwachte API- of hostingkosten. (Mitigatie: Gebruik free tiers waar mogelijk, monitoring).
11. Succescriteria (MVP):

MVP applicatie succesvol geïmplementeerd en testbaar op een staging omgeving.
Kern-pipeline (upload t/m generatie) functioneert technisch.
Eerste UAT succesvol afgerond met constructieve feedback over de bruikbaarheid en kwaliteit van de gegenereerde MVP-secties.
Het projectteam heeft voldoende geleerd om beslissingen te nemen over vervolgontwikkeling en prioriteiten voor post-MVP fases.
12. Benodigdheden (Globaal):

Ontwikkeltijd en -expertise (Python, FastAPI, Vue.js, Supabase, AI/Prompting, Docker).
Toegang tot Supabase (gratis tier mogelijk voldoende voor MVP).
Toegang tot Google AI API (Gemini) (gratis quota of budget nodig).
Hosting omgeving voor MVP staging (gratis/low-cost tiers mogelijk).
Tijd van 1-2 arbeidsdeskundigen voor UAT.