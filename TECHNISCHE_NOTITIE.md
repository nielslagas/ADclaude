# Technische Notitie: Rapport Weergave Probleem

## Probleembeschrijving
Er was een probleem met het weergeven van rapporten in de frontend. Hoewel rapporten correct werden gegenereerd en opgeslagen in de database, werden deze niet weergegeven in de gebruikersinterface. De API gaf de raportgegevens correct terug (inclusief inhoud), maar de frontend toonde de inhoud niet.

## Root Cause Analysis
Na grondig onderzoek zijn twee hoofdoorzaken geïdentificeerd:

1. **Veldnaam inconsistentie:** Er was een mismatch tussen de databaseschema en het SQLModel ORM model:
   - In de database werd het veld `content` gebruikt voor de rapport-inhoud
   - In het SQLModel was het veld `content_json` genoemd
   - In de frontend TypeScript interface werd `content` verwacht

2. **Gereserveerde keyword in SQLAlchemy:** Het veld `metadata` in het model veroorzaakte conflicten omdat dit een gereserveerd woord is in SQLAlchemy's declaratieve API.

3. **JSON Serialisatie/Deserialisatie:** De JSON-gegevens in de content en metadata velden werden niet consistent verwerkt:
   - PostgreSQL slaat deze op als JSONB
   - Bij het ophalen moesten deze expliciet als dictionaries worden geparsed
   - De frontend verwachtte een dictionary structuur

## Geïmplementeerde Oplossing

1. **ORM Model Updates:**
   - Het `content_json` veld in Report model is hernoemd naar `content` om overeen te komen met het databaseschema
   - Het `report_metadata` veld is gecreëerd met een expliciete column mapping naar het database `metadata` veld
   - `SQLAlchemy Column` is direct gebruikt in plaats van Field/sa_column voor betere controle

2. **Verbeterd JSON Beheer:**
   - Toegevoegd JSON parsing in de `database_service.get_rows` en `get_row_by_id` methoden
   - Een aangepaste UUIDEncoder toegevoegd om UUID objecten correct naar JSON te serialiseren
   - Logica toegevoegd om zowel `metadata` als `report_metadata` veldnamen correct af te handelen

3. **Code Refactoring:**
   - Alle referenties naar de oude veldnamen bijgewerkt voor consistentie
   - Frontend TypeScript interfaces bijgewerkt om overeen te komen met API-respons

## Technische Details

### Database Services
```python
# Custom JSON encoder voor UUID objecten
class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

# JSON parsing bij ophalen rapport data
if "content" in row and isinstance(row["content"], str):
    try:
        row["content"] = json.loads(row["content"])
    except json.JSONDecodeError:
        print(f"Failed to decode content JSON: {row['content']}")
```

### SQLModel Definitie
```python
# Gebruik van Column direct om metadata conflict te vermijden
report_metadata: Optional[Dict[str, Any]] = Field(
    default=None, 
    sa_column=Column("metadata", JSON, nullable=True)
)
```

### Frontend TypeScript Interface
```typescript
export interface Report {
  id: string;
  title: string;
  template_id: string;
  status: string;
  case_id: string;
  created_at: string;
  updated_at?: string;
  content?: Record<string, string>;
  error?: string;
}
```

## Resultaat
Na implementatie van deze oplossingen:
- Rapporten worden correct weergegeven in de frontend
- De API geeft consistente JSON structuren terug
- UUID objecten worden correct geserialiseerd/gedeserialiseerd
- De applicatie kan nu succesvol gegenereerde rapporten tonen en opslaan

## Leerpunten
1. Zorg voor consistente naamgeving tussen databaseschema's en ORM modellen
2. Vermijd het gebruik van gereserveerde sleutelwoorden in SQL/ORM modellen
3. Implementeer expliciete JSON parsing/serializatie voor complexe datastructuren
4. Gebruik gedetailleerde logging om problemen met gegevensparsing snel te identificeren

## Toekomstige Aanbevelingen
1. Voeg expliciete validatie toe voor JSON velden bij het opslaan en ophalen
2. Overweeg het gebruik van expliciete serializers/deserializers in plaats van directe JSON parsing
3. Implementeer end-to-end tests die specifiek de JSON verwerkingspipeline valideren

---
Datum: 8 mei 2025
Auteur: Ontwikkelteam AI-Arbeidsdeskundige