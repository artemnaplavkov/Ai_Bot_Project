import pandas as pd
import numpy as np
import spacy
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import classification_report, accuracy_score
import joblib

nlp = spacy.load("ru_core_news_md")

def text_to_vector(text):
    doc = nlp(text)
    if len(doc) == 0:
        return np.zeros(nlp.meta["vectors"]["width"])
    return doc.vector

df = pd.read_csv("dataset.csv", encoding="utf-8")
X = np.array([text_to_vector(t) for t in df["text"]])
y = df["intent"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)


clf = make_pipeline(
    StandardScaler(), 
    LinearSVC(C=1.0, max_iter=2000, random_state=42)
)
clf.fit(X_train, y_train)

y_pred = clf.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print(classification_report(y_test, y_pred))

joblib.dump(clf, "intent_model_spacy.pkl")
