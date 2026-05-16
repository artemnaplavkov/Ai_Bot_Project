import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import torch
torch.cuda.is_available = lambda: False
torch.cuda.device_count = lambda: 0

import pandas as pd
from sklearn.model_selection import train_test_split
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from sklearn.metrics import accuracy_score, classification_report
import json
import os as _os

df = pd.read_csv("dataset_extended.csv")

print("Уникальные интенты в датасете:")
print(df["intent"].value_counts())

label2id = {label: idx for idx, label in enumerate(sorted(df["intent"].unique()))}
id2label = {v: k for k, v in label2id.items()}
df["label"] = df["intent"].map(label2id)

print(f"\nВсего классов: {len(label2id)}")
print("Маппинг интентов:", label2id)

train_texts, val_texts, train_labels, val_labels = train_test_split(
    df["text"].tolist(), df["label"].tolist(), test_size=0.2, random_state=42
)

MODEL_NAME = "DeepPavlov/rubert-base-cased"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=len(label2id))

def tokenize(texts):
    return tokenizer(texts, padding=True, truncation=True, return_tensors="pt", max_length=128)

train_encodings = tokenize(train_texts)
val_encodings = tokenize(val_texts)

class IntentDataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels
    
    def __getitem__(self, idx):
        item = {key: val[idx] for key, val in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx])
        return item
    
    def __len__(self):
        return len(self.labels)

train_dataset = IntentDataset(train_encodings, train_labels)
val_dataset = IntentDataset(val_encodings, val_labels)

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    predictions = predictions.argmax(axis=-1)
    return {"accuracy": accuracy_score(labels, predictions)}

training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=10,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    logging_steps=10,
    learning_rate=2e-5,
    warmup_ratio=0.1,
    weight_decay=0.01,
    load_best_model_at_end=True,
    metric_for_best_model="accuracy",
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics
)

print("\nНачинаем обучение...")
trainer.train()

print("\nОценка модели:")
predictions = trainer.predict(val_dataset)
preds = predictions.predictions.argmax(axis=-1)
print(classification_report(val_labels, preds, target_names=list(label2id.keys())))

_os.makedirs("intent_model_extended", exist_ok=True)
model.save_pretrained("intent_model_extended")
tokenizer.save_pretrained("intent_model_extended")

with open("intent_model_extended/label2id.json", "w", encoding="utf-8") as f:
    json.dump(label2id, f, ensure_ascii=False, indent=2)

print(f"\nМодель сохранена в intent_model_extended/ с {len(label2id)} классами")

test_texts = ["помощь", "привет", "погода", "сколько времени", "пока", "спасибо"]
print("\nТестирование модели:")
for text in test_texts:
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
        pred = outputs.logits.argmax(dim=-1).item()
        intent = id2label[pred]
        print(f"  '{text}' -> {intent}")