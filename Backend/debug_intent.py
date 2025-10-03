import os
os.environ.setdefault("SECRET_KEY", "12345678901234567890123456789012")
os.environ.setdefault("API_KEY_BACKEND", "1234567890abcdef")

from src.application.nlp.intent_classifier import IntentClassifier

classifier = IntentClassifier()
queries = [
    "Buenos días",
    "Análisis general",
    "Estado actual de los datos",
    "Texto completamente aleatorio sin sentido"
]
for query in queries:
    result = classifier.classify(query)
    print(query, '->', result.intent, result.confidence, result.reasoning)
