# Instructies voor het wijzigen van LLM-provider

Je hebt nu de mogelijkheid om verschillende LLM-providers te gebruiken voor het genereren van rapporten. De toepassing ondersteunt:

- Google (Gemini)
- OpenAI (GPT-4o)
- Anthropic (Claude)

## 1. Configuratie

Om de provider te wijzigen, moet je de volgende omgevingsvariabelen instellen in je `.env` bestand:

```
# Kies één provider: google, openai, of anthropic
LLM_PROVIDER=anthropic

# Provider-specifieke API-sleutels
GOOGLE_API_KEY=jouw_google_api_sleutel
OPENAI_API_KEY=jouw_openai_api_sleutel
ANTHROPIC_API_KEY=jouw_anthropic_api_sleutel

# Specifieke modelconfiguratie (optioneel)
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-3-opus-20240229
```

## 2. Provider-specifieke instellingen

### Google Gemini
- Standaardmodel: `gemini-1.5-pro`
- API-sleutel verkrijgen: https://ai.google.dev/
- Kosten: ~$0.0007 per 1K tokens

### OpenAI GPT-4o
- Standaardmodel: `gpt-4o`
- API-sleutel verkrijgen: https://platform.openai.com/
- Kosten: ~$0.005 per 1K tokens (input), ~$0.015 per 1K tokens (output)

### Anthropic Claude
- Standaardmodel: `claude-3-opus-20240229`
- Alternatieve modellen: `claude-3-haiku-20240307`, `claude-3-sonnet-20240229`
- API-sleutel verkrijgen: https://console.anthropic.com/
- Kosten: ~$0.015 per 1K tokens (input), ~$0.075 per 1K tokens (output)

## 3. Uitvoeren met nieuwe provider

Na het wijzigen van de configuratie moet je de containers opnieuw starten:

```bash
docker-compose down
docker-compose up -d
```

## 4. Aanbevelingen voor providers

Elke provider heeft zijn eigen sterke punten:

- **Google Gemini**: Goed geprijsd, maar kan eerder inhoud blokkeren vanwege strenge veiligheidsfilters
- **OpenAI GPT-4o**: Uitstekende prestaties en minder strenge veiligheidsfilters, hogere kosten
- **Anthropic Claude**: Zeer goede prestaties met langere contexten, hogere kosten

Voor deze specifieke toepassing, waarbij sommige medische termen mogelijk problemen opleveren met veiligheidsfilters, kan OpenAI of Anthropic betere resultaten geven dan Google Gemini.

## 5. Embeddings

Standaard wordt Google Gemini gebruikt voor embeddings, tenzij je OpenAI als hoofdprovider kiest. In dat geval wordt OpenAI gebruikt voor embeddings. Dit zorgt voor optimale compatibiliteit tussen zoek- en generatiefuncties.

## 6. Foutmeldingen en oplossingen

Als je "dangerous content" foutmeldingen blijft zien:

1. Controleer of je voldoende krediet hebt bij je huidige provider
2. Probeer een andere provider (OpenAI of Anthropic hebben vaak minder strenge filters)
3. Voer het script `clean_existing_reports.py` uit om bestaande rapporten met fouten op te schonen
4. Probeer een nieuw rapport te genereren

## 7. Feedback en ondersteuning

Als je problemen ondervindt met een specifieke provider, laat het ons weten via het ticketsysteem. Vermeld daarbij:
- Welke provider je gebruikt
- Wat voor soort documenten je verwerkt
- Welke foutmeldingen je ziet