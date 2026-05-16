import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import torch
torch.cuda.is_available = lambda: False
torch.cuda.device_count = lambda: 0
import pandas as pd
from sklearn.model_selection import train_test_split
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments

MODEL_NAME = "DeepPavlov/rubert-base-cased"  # или "cointegrated/rubert-tiny2" для скорости
df = pd.read_csv("dataset.csv")  # колонки: text, intent

label2id = {label: idx for idx, label in enumerate(df.intent.unique())}
id2label = {v: k for k, v in label2id.items()}
df["label"] = df.intent.map(label2id)

train_texts, val_texts, train_labels, val_labels = train_test_split(
    df.text.tolist(), df.label.tolist(), test_size=0.2, random_state=42
)

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

training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=4,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    logging_dir="./logs",
    logging_steps=100,
    learning_rate=2e-5,
    save_steps=500,
    save_total_limit=2,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    # eval_dataset=val_dataset,  # временно убираем валидацию
)
trainer.train()

# Сохраняем модель и маппинги
model.save_pretrained("intent_model")
tokenizer.save_pretrained("intent_model")

import json
with open("intent_model/label2id.json", "w", encoding="utf-8") as f:
    json.dump(label2id, f, ensure_ascii=False)
with open("intent_model/id2label.json", "w", encoding="utf-8") as f:
    json.dump(id2label, f, ensure_ascii=False)

print("Модель обучена и сохранена в папку intent_model")