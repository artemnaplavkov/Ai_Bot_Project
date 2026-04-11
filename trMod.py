import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import joblib

df = pd.read_csv("dataset.csv")
X = df["text"]
y = df["intent"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)


pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 3))),
    ("clf", LogisticRegression(max_iter=1000, random_state=42))
])


pipeline.fit(X_train, y_train)


accuracy = pipeline.score(X_test, y_test)
print(f"Accuracy: {accuracy:.2f}")


joblib.dump(pipeline, "intent_model.pkl")
print("Модель сохранена в intent_model.pkl")