import numpy as np
import spacy
from sklearn.base import BaseEstimator, TransformerMixin


class SpacyVectorizer(BaseEstimator, TransformerMixin):
    def __init__(self, model_name="ru_core_news_md"):
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            print(f"Модель {model_name} не найдена, загружаем ru_core_news_sm...")
            try:
                self.nlp = spacy.load("ru_core_news_sm")
            except OSError:
                print("Модель spaCy не найдена. Установите: python -m spacy download ru_core_news_md")
                raise
        self.vector_size = self.nlp("тест").vector.shape[0]

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        vectors = []
        for text in X:
            doc = self.nlp(str(text))
            if len(doc) == 0:
                vectors.append(np.zeros(self.vector_size))
            else:
                vectors.append(doc.vector)
        return np.array(vectors)


class SimpleVectorizer:
    def __init__(self, model_name="ru_core_news_md"):
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            self.nlp = spacy.load("ru_core_news_sm")
        self.vector_size = self.nlp("тест").vector.shape[0]
    
    def vectorize(self, text):
        doc = self.nlp(str(text))
        if len(doc) == 0:
            return np.zeros(self.vector_size)
        return doc.vector
    
    def vectorize_batch(self, texts):
        vectors = []
        for text in texts:
            vectors.append(self.vectorize(text))
        return np.array(vectors)


def get_vectorizer():
    return SpacyVectorizer()


def text_to_vector(text, model_name="ru_core_news_md"):
    nlp = spacy.load(model_name)
    doc = nlp(text)
    return doc.vector