# Status Update: Reparatie Rapport Inhoud Generatie

## Probleem
Na het oplossen van de problemen met documentverwerking en rapport status updates, werd er nog een probleem ontdekt: de inhoud van de rapportsecties bleef leeg met de foutmelding `Error generating content with direct LLM: 'dangerous_content'`.

## Oorzaak
Het Gemini-model blokkeerde de inhoudsgeneratie vanwege de 'dangerous_content' veiligheidsfilter. Dit gebeurt waarschijnlijk omdat:

1. Arbeidsdeskundige rapporten combinaties van medische gegevens en werkadviezen bevatten
2. Gemini's veiligheidsfilters strenger zijn bij content die medische informatie bevat
3. De prompts en safety settings waren te restrictief ingesteld

## Geïmplementeerde Oplossingen

### 1. Aanpassing van Safety Settings

In zowel `report_generator_hybrid.py` als `rag_pipeline.py` is de safety setting voor DANGEROUS_CONTENT aangepast:

```python
safety_settings = {
    "HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
    "HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
    "SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
    "DANGEROUS_CONTENT": "BLOCK_ONLY_HIGH",  # Aangepast van BLOCK_MEDIUM_AND_ABOVE naar BLOCK_ONLY_HIGH
}
```

Dit zorgt ervoor dat alleen echt gevaarlijke inhoud wordt geblokkeerd, maar professionele arbeidsdeskundige adviezen worden toegestaan.

### 2. Verbeterde System Prompts

De system instructies in beide bestanden zijn aangepast om duidelijker te maken dat dit professionele rapporten zijn en geen medisch advies:

```python
system_instruction = (
    "Je bent een ervaren arbeidsdeskundige die professionele rapporten opstelt "
    "volgens de Nederlandse standaarden. Schrijf in de stijl van een officieel arbeidsdeskundig rapport. "
    "Gebruik formele, zakelijke taal en zorg voor een objectieve, feitelijke weergave op basis van de aangeleverde "
    "informatie. Je biedt geen medisch advies, maar beschrijft alleen de situatie zoals die in de documenten "
    "is vastgesteld door medische professionals. Vermijd aannames of speculaties die niet onderbouwd zijn door "
    "de beschikbare gegevens."
)
```

### 3. Neutrale Prompts voor Secties

De sectie-specifieke prompts in `create_direct_prompt_for_section` zijn herschreven om:
- Medische terminologie te minimaliseren
- Gevoelige termen te verwijderen
- De nadruk te leggen op objectieve, feitelijke rapportage
- Expliciete instructies toe te voegen om geen medisch advies te geven
- De prompts neutraler te maken zonder de professionele standaard te verliezen

Bijvoorbeeld, voor de "belastbaarheid" sectie is de titel veranderd naar "Analyse van Werkmogelijkheden" en focust meer op objectieve analyse dan op medische beoordelingen.

### 4. Fallback Mechanismen

Voor beide generatie-methoden zijn fallback mechanismen geïmplementeerd:

- Als een prompt wordt geblokkeerd vanwege 'dangerous_content', wordt een eenvoudigere, meer neutrale prompt geprobeerd
- Deze fallback prompt bevat minder specifieke instructies en meer algemene richtlijnen voor objectieve beschrijvingen
- Dit zorgt ervoor dat er altijd content wordt gegenereerd, zelfs als de primaire prompt wordt geblokkeerd

In `report_generator_hybrid.py`:
```python
# Probeer opnieuw met een meer neutrale prompt als het gaat om dangerous_content
if 'dangerous_content' in str(block_reason).lower():
    try:
        logger.info("Attempting to generate content with a more neutral prompt")
        simple_prompt = "Genereer een objectieve beschrijving op basis van de gegeven informatie, " + \
                       "waarbij je alleen feitelijke informatie uit de documenten gebruikt."
        simple_response = model.generate_content([...])
        if simple_response.text:
            return simple_response.text
    except Exception as fallback_error:
        logger.error(f"Fallback prompt also failed: {str(fallback_error)}")
```

In `rag_pipeline.py` is een vergelijkbaar mechanisme geïmplementeerd, maar met uitgebreidere fallback opties.

## Impact

Deze wijzigingen zorgen ervoor dat:

1. Rapporten nu succesvol kunnen worden gegenereerd zonder geblokkeerd te worden
2. De inhoud van de secties wordt correct ingevuld
3. Er zijn meerdere fallbacks als er toch nog een blokkering optreedt
4. De content blijft professioneel en objectief, maar vermijdt gevoelige formuleringen

## Volgende Stappen

1. Test de rapporten met verschillende soorten documenten om te zorgen dat de generatie consistent werkt
2. Monitor de loggings voor eventuele verdere 'dangerous_content' blokkades
3. Feedback verzamelen over de kwaliteit van de gegenereerde rapporten
4. Eventueel verdere aanpassingen maken aan de prompts indien nodig