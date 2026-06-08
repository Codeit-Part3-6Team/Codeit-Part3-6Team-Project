from __future__ import annotations

from pathlib import Path
from typing import Any

from src.metrics import accuracy


MODEL_TYPE = "huggingface_sequence_classifier"


def is_huggingface_model(name: str) -> bool:
    """Return True when a config model name should use the HuggingFace path."""
    return name == MODEL_TYPE


class _TextDataset:
    """Minimal torch Dataset that tokenizes rows on access."""

    def __init__(
        self,
        rows: list[dict[str, str]],
        tokenizer: Any,
        label2id: dict[str, int],
        text_col: str,
        label_col: str,
        max_length: int,
    ) -> None:
        self.rows = rows
        self.tokenizer = tokenizer
        self.label2id = label2id
        self.text_col = text_col
        self.label_col = label_col
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, Any]:
        import torch

        row = self.rows[index]
        encoded = self.tokenizer(
            row[self.text_col],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )
        item = {key: value.squeeze(0) for key, value in encoded.items()}
        item["labels"] = torch.tensor(self.label2id[row[self.label_col]], dtype=torch.long)
        return item


class HuggingFaceSequenceClassifier:
    """Adapter for fine-tuning HuggingFace sequence classification models.

    The rest of the scaffold uses small JSON-serializable smoke models. A
    HuggingFace model also needs tokenizer files and model weights, so this
    adapter saves both metadata (`best_model.json`) and a `hf_model/` directory.
    """

    def __init__(
        self,
        model_name: str,
        label2id: dict[str, int],
        max_length: int = 128,
    ) -> None:
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise ImportError(
                "HuggingFace 모델을 사용하려면 transformers와 torch가 필요합니다. "
                "`pip install -r requirements.txt`를 먼저 실행하세요."
            ) from exc

        self.model_name = model_name
        self.label2id = label2id
        self.id2label = {index: label for label, index in label2id.items()}
        self.max_length = max_length
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            num_labels=len(label2id),
            id2label=self.id2label,
            label2id=label2id,
        )

    @classmethod
    def from_artifact(cls, artifact_dir: str | Path) -> "HuggingFaceSequenceClassifier":
        """Load tokenizer/model weights from a saved experiment directory."""
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise ImportError(
                "HuggingFace 모델을 불러오려면 transformers와 torch가 필요합니다."
            ) from exc

        import json

        artifact = Path(artifact_dir)
        metadata = json.loads((artifact / "best_model.json").read_text(encoding="utf-8"))
        instance = cls.__new__(cls)
        instance.model_name = metadata["base_model_name"]
        instance.label2id = {key: int(value) for key, value in metadata["label2id"].items()}
        instance.id2label = {int(key): value for key, value in metadata["id2label"].items()}
        instance.max_length = int(metadata["max_length"])
        model_dir = artifact / metadata["model_dir"]
        instance.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        instance.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        return instance

    def fit(
        self,
        train_rows: list[dict[str, str]],
        valid_rows: list[dict[str, str]],
        output_dir: str | Path,
        train_config: dict[str, Any],
        text_col: str = "text",
        label_col: str = "label",
    ) -> tuple[dict[str, float], list[dict[str, float]]]:
        """Fine-tune for the configured number of epochs and return metrics/history."""
        import torch
        from torch.optim import AdamW
        from torch.utils.data import DataLoader

        epochs = int(train_config.get("epochs", 1))
        batch_size = int(train_config.get("batch_size", 8))
        optimizer_config = train_config.get("optimizer", {})
        lr = float(optimizer_config.get("lr", 2e-5))
        weight_decay = float(optimizer_config.get("weight_decay", 0.01))

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(device)

        train_dataset = _TextDataset(
            train_rows,
            self.tokenizer,
            self.label2id,
            text_col,
            label_col,
            self.max_length,
        )
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        optimizer = AdamW(self.model.parameters(), lr=lr, weight_decay=weight_decay)

        history: list[dict[str, float]] = []
        for epoch in range(1, epochs + 1):
            self.model.train()
            total_loss = 0.0
            for batch in train_loader:
                batch = {key: value.to(device) for key, value in batch.items()}
                optimizer.zero_grad()
                outputs = self.model(**batch)
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                total_loss += float(loss.detach().cpu())

            valid_pred = self.predict([row[text_col] for row in valid_rows], batch_size=batch_size)
            valid_true = [row[label_col] for row in valid_rows]
            row_metrics = {
                "epoch": float(epoch),
                "train_loss": total_loss / max(len(train_loader), 1),
                "valid_accuracy": accuracy(valid_true, valid_pred),
            }
            history.append(row_metrics)

        self.save(output_dir)
        metrics = {
            "valid_accuracy": history[-1]["valid_accuracy"] if history else 0.0,
        }
        return metrics, history

    def predict(self, texts: list[str], batch_size: int = 8) -> list[str]:
        """Predict labels for a list of texts."""
        import torch
        from torch.utils.data import DataLoader, TensorDataset

        device = next(self.model.parameters()).device
        encoded = self.tokenizer(
            texts,
            truncation=True,
            padding=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        dataset = TensorDataset(
            encoded["input_ids"],
            encoded["attention_mask"],
        )
        loader = DataLoader(dataset, batch_size=batch_size)

        predictions: list[str] = []
        self.model.eval()
        with torch.no_grad():
            for input_ids, attention_mask in loader:
                outputs = self.model(
                    input_ids=input_ids.to(device),
                    attention_mask=attention_mask.to(device),
                )
                label_ids = outputs.logits.argmax(dim=-1).detach().cpu().tolist()
                predictions.extend(self.id2label[int(label_id)] for label_id in label_ids)
        return predictions

    def predict_one(self, text: str) -> str:
        """Predict one label for one text."""
        return self.predict([text])[0]

    def save(self, output_dir: str | Path) -> None:
        """Save tokenizer and model weights to `hf_model/`."""
        model_dir = Path(output_dir) / "hf_model"
        model_dir.mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(model_dir)
        self.tokenizer.save_pretrained(model_dir)

    def to_dict(self) -> dict[str, Any]:
        """Return metadata needed to reload the HuggingFace artifact."""
        return {
            "model_type": MODEL_TYPE,
            "base_model_name": self.model_name,
            "model_dir": "hf_model",
            "label2id": self.label2id,
            "id2label": {str(key): value for key, value in self.id2label.items()},
            "max_length": self.max_length,
        }


def build_label_map(rows: list[dict[str, str]], label_col: str = "label") -> dict[str, int]:
    """Build a deterministic label-to-id map when no class_map.json is configured."""
    labels = sorted({row[label_col] for row in rows})
    return {label: index for index, label in enumerate(labels)}
