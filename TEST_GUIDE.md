# AI-Arbeidsdeskundige Test Guide

## 🚀 Quick Start Testing

### 1. Start de Services
```bash
docker-compose up -d
```

Wacht tot alle services healthy zijn:
```bash
docker-compose ps
```

### 2. Open de Frontend
Open browser: http://localhost:3000

### 3. Test Flow

#### A. Document Upload Test
1. Login met test credentials
2. Maak nieuwe case aan:
   - Titel: "Test Structured Output"
   - Client: "Jan Jansen"
3. Upload test document (gebruik een van de voorbeelden in `Arbeidsdeskundige data/`)
4. Wacht op processing (check status in UI)

#### B. Report Generation Test
1. Ga naar de case
2. Klik "Generate Report"
3. Selecteer template: "Staatvandienst Format"
4. Wacht op generatie
5. Bekijk rapport in verschillende templates:
   - Standaard
   - Modern
   - Professioneel
   - Compact

#### C. Export Test
1. Export naar Word (.docx)
2. Export naar PDF
3. Check formatting en structure

## 🧪 Automated Testing

### Complete Flow Test
```bash
# Maakt test case, upload document, genereert rapport
./test_complete_flow.sh
```

Dit creëert:
- `test_report_output.json` - Complete API response met structured data
- `test_report.html` - HTML formatted output
- `test_report.md` - Markdown output
- `test_report.docx` - Word document

### Integration Test (in Docker)
```bash
docker-compose exec backend-api python test_integration_structured.py
```

### Unit Test Structured Output
```bash
docker-compose exec backend-api python test_structured_output.py
```

## 🔍 Wat te Controleren

### 1. Structured Output
Check in `test_report_output.json`:
```json
{
  "structured_content": {
    "section_id": "belastbaarheid",
    "title": "Belastbaarheid",
    "summary": "...",
    "main_content": [
      {
        "type": "assessment",
        "content": [...]
      }
    ],
    "conclusions": [...],
    "recommendations": [...]
  }
}
```

### 2. Belastbaarheid Sectie
Moet bevatten:
- **Assessment matrix** met fysiek/mentaal/sociaal
- **Specifieke capaciteiten** (bijv. "tillen: max 5kg")
- **Frequenties** (dagelijks, incidenteel)
- **Beperkingen** per aspect
- **Prioriteit aanbevelingen**

### 3. Matching Sectie
Moet bevatten:
- **Criteria lijsten** met prioriteit [E]ssentieel / [W]enselijk
- **Categorieën**: fysieke omgeving, taakinhoud, werktijden
- **Geschikte functies** lijst

### 4. Frontend Display
- Headers moeten blauw zijn (#1e40af, #2563eb, #3b82f6)
- Tabellen voor assessments
- Bullets voor lijsten
- Prioriteit indicators voor aanbevelingen

## 📊 Performance Testing

### Check Processing Time
```bash
# Monitor logs tijdens processing
docker-compose logs -f backend-worker
```

### Check Memory Usage
```bash
docker stats
```

## 🐛 Troubleshooting

### API Not Responding
```bash
docker-compose restart backend-api
```

### Worker Not Processing
```bash
docker-compose restart backend-worker
docker-compose logs backend-worker
```

### Database Issues
```bash
docker-compose exec db psql -U postgres -d arbeidsdeskundige
\dt  # list tables
\q   # quit
```

### Clear Test Data
```bash
docker-compose exec db psql -U postgres -d arbeidsdeskundige -c "DELETE FROM reports WHERE title LIKE '%Test%';"
```

## ✅ Success Criteria

1. **Structured Data**: Elke sectie heeft `structured_content` in response
2. **Format Conversion**: HTML, Markdown, JSON outputs werken
3. **Assessment Matrix**: Belastbaarheid toont tabel met capaciteiten
4. **Recommendations**: Prioriteiten correct weergegeven
5. **Export**: Word document heeft correcte formatting
6. **Performance**: Report generatie < 30 seconden

## 📝 Test Checklist

- [ ] Services starten zonder errors
- [ ] Document upload succesvol
- [ ] Document processing compleet
- [ ] Report generatie werkt
- [ ] Structured content aanwezig in API response
- [ ] Belastbaarheid sectie heeft assessment matrix
- [ ] Matching sectie heeft criteria lijsten
- [ ] Frontend toont rapport correct
- [ ] Templates (Standaard/Modern/etc) werken
- [ ] Word export heeft juiste formatting
- [ ] PDF export is leesbaar
- [ ] Performance acceptabel (< 30s per rapport)

## 🎯 Next Steps

Na succesvolle tests:

1. **Production Deployment**
   - Update environment variables
   - Set production API keys
   - Configure domain and SSL

2. **User Testing**
   - Test met echte arbeidsdeskundige rapporten
   - Gather feedback op output kwaliteit
   - Fine-tune prompts indien nodig

3. **Monitoring**
   - Set up Grafana dashboards
   - Configure alerts
   - Monitor API performance