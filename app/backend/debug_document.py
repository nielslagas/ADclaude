"""
Debug script to manually process a document and identify issues.
"""
import sys
import os

# Voeg de app directory toe aan het Python pad
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tasks.process_document_tasks.debug_document_processor import debug_document_processing

# Document ID's van de documenten die vastlopen
DOCUMENT_IDS = [
    'b6188993-739e-4fb9-a53b-b4567b0e643b',  # Meest recente document
    '74f9fff0-c48f-4852-a41b-0e5e4e57b6cc',  # Eerder document
]

if __name__ == "__main__":
    print("Starting debug document processing...")
    for doc_id in DOCUMENT_IDS:
        print(f"Processing document: {doc_id}")
        debug_document_processing(doc_id)
    print("Debug processing complete. Check /app/debug_processing.log for results.")