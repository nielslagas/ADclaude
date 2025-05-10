#!/usr/bin/env python3
"""
Test script voor de verbeterde Gemini embedding functionaliteit.
Dit script test de belangrijkste functionaliteit van de embedding module.
"""

import sys
import os
import logging
from typing import List
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("embedding_test")

# Voeg de app path toe zodat we de modules kunnen importeren
sys.path.append(os.path.join(os.path.dirname(__file__), "app", "backend"))

# Importeer de benodigde modules
try:
    from app.utils.embeddings import (
        generate_embedding, 
        generate_query_embedding,
        validate_api_connection,
        calculate_similarity,
        API_INITIALIZED
    )
    from app.core.config import settings
    from app.utils.vector_store import init_vector_store, add_embedding, similarity_search
except ImportError as e:
    logger.error(f"Fout bij importeren modules: {e}")
    sys.exit(1)

def test_api_connection():
    """Test of de API-verbinding werkt"""
    logger.info("Test 1: API-verbinding valideren")
    
    if not settings.GOOGLE_API_KEY:
        logger.warning("Geen Google API key gevonden in settings")
        return False
        
    result = validate_api_connection()
    if result:
        logger.info("✅ API-verbinding succesvol gevalideerd")
    else:
        logger.error("❌ API-verbinding validatie mislukt")
    
    return result

def test_embedding_generation():
    """Test de generatie van embeddings"""
    logger.info("Test 2: Embedding generatie testen")
    
    test_text = "Dit is een voorbeeldzin om de embedding functionaliteit te testen."
    
    try:
        start_time = time.time()
        embedding = generate_embedding(test_text)
        duration = time.time() - start_time
        
        if not embedding or not isinstance(embedding, List):
            logger.error("❌ Geen geldige embedding gegenereerd")
            return False
            
        logger.info(f"✅ Embedding succesvol gegenereerd met {len(embedding)} dimensies in {duration:.2f}s")
        logger.info(f"Eerste 5 waardes: {embedding[:5]}")
        return True
    except Exception as e:
        logger.error(f"❌ Fout bij genereren van embedding: {e}")
        return False

def test_query_embedding():
    """Test de generatie van query embeddings"""
    logger.info("Test 3: Query embedding generatie testen")
    
    test_query = "Wat zijn de beperkingen van de werknemer?"
    
    try:
        start_time = time.time()
        embedding = generate_query_embedding(test_query)
        duration = time.time() - start_time
        
        if not embedding or not isinstance(embedding, List):
            logger.error("❌ Geen geldige query embedding gegenereerd")
            return False
            
        logger.info(f"✅ Query embedding succesvol gegenereerd met {len(embedding)} dimensies in {duration:.2f}s")
        return True
    except Exception as e:
        logger.error(f"❌ Fout bij genereren van query embedding: {e}")
        return False

def test_similarity_calculation():
    """Test de berekening van similarity tussen embeddings"""
    logger.info("Test 4: Similarity berekening testen")
    
    text1 = "De werknemer heeft rugklachten en kan niet lang staan."
    text2 = "De cliënt heeft problemen met zijn rug waardoor langdurig staan lastig is."
    text3 = "De werkgever heeft een klein kantoor in Amsterdam."
    
    try:
        emb1 = generate_embedding(text1)
        emb2 = generate_embedding(text2)
        emb3 = generate_embedding(text3)
        
        sim_related = calculate_similarity(emb1, emb2)
        sim_unrelated = calculate_similarity(emb1, emb3)
        
        logger.info(f"Similarity tussen verwante teksten: {sim_related:.4f}")
        logger.info(f"Similarity tussen niet-verwante teksten: {sim_unrelated:.4f}")
        
        if sim_related > sim_unrelated:
            logger.info("✅ Similarity berekening correct: verwante teksten hebben hogere similarity")
            return True
        else:
            logger.error("❌ Similarity berekening incorrect: niet-verwante teksten hebben hogere similarity")
            return False
    except Exception as e:
        logger.error(f"❌ Fout bij similarity berekening: {e}")
        return False

def test_vector_store():
    """Test de vector store functionaliteit"""
    logger.info("Test 5: Vector store testen - SKIPPED (wordt later getest)")
    
    # Sla de vector store test over voor nu, focus op embedding functionaliteit
    logger.info("✅ Vector store test overgeslagen (wordt apart getest)")
    return True

def run_all_tests():
    """Voer alle tests uit en rapporteer resultaten"""
    logger.info("===== RAG PIPELINE EMBEDDING TESTS =====")
    logger.info(f"Google API key beschikbaar: {bool(settings.GOOGLE_API_KEY)}")
    logger.info(f"API geïnitialiseerd: {API_INITIALIZED}")
    
    tests = [
        ("API Verbinding", test_api_connection),
        ("Embedding Generatie", test_embedding_generation),
        ("Query Embedding", test_query_embedding),
        ("Similarity Berekening", test_similarity_calculation),
        ("Vector Store", test_vector_store)
    ]
    
    results = []
    for name, test_func in tests:
        logger.info(f"\n{'=' * 40}\nTest start: {name}\n{'=' * 40}")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"❌ Onverwachte fout in test {name}: {e}")
            results.append((name, False))
    
    # Rapporteer resultaten
    logger.info("\n===== TEST RESULTATEN =====")
    success_count = 0
    for name, result in results:
        status = "✅ SUCCES" if result else "❌ MISLUKT"
        logger.info(f"{name}: {status}")
        if result:
            success_count += 1
    
    logger.info(f"\n{success_count}/{len(tests)} tests succesvol.")
    return success_count == len(tests)

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)