import numpy as np
import spacy
from sklearn.base import BaseEstimator, TransformerMixin

class SpacyVectorizer(BaseEstimator, TransformerMixin):
    def __init__(self):
        self.nlp = spacy.load("ru_core_news_md")
        self.vector_size = self.nlp("test").vector.shape[0]

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        vectors = []
        for text in X:
            doc = self.nlp(text)
            if len(doc) == 0:
                vectors.append(np.zeros(self.vector_size))
            else:
                vectors.append(doc.vector)
        return np.array(vectors)