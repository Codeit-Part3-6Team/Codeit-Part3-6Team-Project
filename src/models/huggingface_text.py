from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.metrics import accuracy


MODEL_TYPE = "huggingface_sequence_classifier"


def is_huggingface_model(name: str) -> bool:
    """config의 model.name이 HuggingFace 전용 경로를 써야 하는지 확인합니다."""
    return name == MODEL_TYPE


class _TextDataset:
    """row를 필요할 때 tokenizer에 통과시키는 최소 torch Dataset입니다."""

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
    """HuggingFace sequence classification 모델을 학습/저장/예측하는 adapter입니다.

    smoke model은 JSON 하나로 저장할 수 있지만, HuggingFace 모델은 tokenizer와
    weight 파일이 필요합니다. 그래서 metadata는 `best_model.json`에 저장하고
    실제 모델 파일은 `hf_model/` 폴더에 저장합니다.
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
        """저장된 실험 폴더에서 tokenizer와 model weight를 다시 불러옵니다."""
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
        """config의 epoch 수만큼 fine-tuning하고 metrics와 history를 반환합니다."""
        import torch
        from torch.optim import AdamW
        from torch.utils.data import DataLoader

        epochs = int(train_config.get("epochs", 1))
        batch_size = int(train_config.get("batch_size", 8))
        optimizer_config = train_config.get("optimizer", {})
        lr = float(optimizer_config.get("lr", 2e-5))
        weight_decay = float(optimizer_config.get("weight_decay", 0.01))
        metric_config = train_config.get("metric", {})
        checkpoint_config = train_config.get("checkpoint", {})
        early_stopping_config = train_config.get("early_stopping", {})
        scheduler_config = train_config.get("scheduler", {})

        # CUDA가 잡히면 그대로 GPU를 쓰고, Colab/로컬 CPU에서도 같은 코드가 돌도록 fallback합니다.
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        resume_from = checkpoint_config.get("resume_from")
        if resume_from:
            self._load_model_checkpoint(resume_from)
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
        scheduler = _build_scheduler(optimizer, scheduler_config, epochs, len(train_loader))
        state = self._load_training_state(resume_from, optimizer, scheduler, device) if resume_from else {}
        start_epoch = int(state.get("epoch", 0)) + 1
        best_score = state.get("best_score")
        no_improve_epochs = int(state.get("no_improve_epochs", 0))
        monitor = str(metric_config.get("monitor", "valid_accuracy"))
        mode = str(metric_config.get("mode", "max"))
        min_delta = float(early_stopping_config.get("min_delta", 0.0))
        patience = int(early_stopping_config.get("patience", 3))

        history: list[dict[str, float]] = []
        for epoch in range(start_epoch, epochs + 1):
            self.model.train()
            total_loss = 0.0
            for batch in train_loader:
                batch = {key: value.to(device) for key, value in batch.items()}
                optimizer.zero_grad()
                outputs = self.model(**batch)
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()
                total_loss += float(loss.detach().cpu())

            # 매 epoch마다 valid 성능을 남겨 history.csv에서 학습 흐름을 볼 수 있게 합니다.
            valid_pred = self.predict([row[text_col] for row in valid_rows], batch_size=batch_size)
            valid_true = [row[label_col] for row in valid_rows]
            row_metrics = {
                "epoch": float(epoch),
                "train_loss": total_loss / max(len(train_loader), 1),
                "valid_accuracy": accuracy(valid_true, valid_pred),
            }
            history.append(row_metrics)
            score = float(row_metrics.get(monitor, row_metrics["valid_accuracy"]))
            improved = _is_improved(score, best_score, mode=mode, min_delta=min_delta)
            if improved:
                best_score = score
                no_improve_epochs = 0
            else:
                no_improve_epochs += 1

            self._save_epoch_checkpoints(
                output_dir=output_dir,
                epoch=epoch,
                metrics=row_metrics,
                checkpoint_config=checkpoint_config,
                optimizer=optimizer,
                scheduler=scheduler,
                best_score=best_score,
                no_improve_epochs=no_improve_epochs,
                improved=improved,
            )

            if early_stopping_config.get("enabled") and no_improve_epochs >= patience:
                break

        self.save(output_dir)
        final_metrics = history[-1] if history else state.get("metrics", {})
        metrics = {
            "valid_accuracy": float(final_metrics.get("valid_accuracy", 0.0)),
        }
        return metrics, history

    def _load_model_checkpoint(self, checkpoint_dir: str | Path) -> None:
        """resume_from 경로의 model/tokenizer weight를 현재 adapter에 불러옵니다."""
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        path = Path(checkpoint_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(path)
        self.tokenizer = AutoTokenizer.from_pretrained(path)

    def _load_training_state(
        self,
        checkpoint_dir: str | Path,
        optimizer: Any,
        scheduler: Any | None,
        device: Any,
    ) -> dict[str, Any]:
        """optimizer/scheduler/trainer_state를 복원해 중단된 학습을 이어갈 수 있게 합니다."""
        import torch

        path = Path(checkpoint_dir)
        optimizer_path = path / "optimizer.pt"
        scheduler_path = path / "scheduler.pt"
        state_path = path / "trainer_state.json"
        if optimizer_path.exists():
            optimizer.load_state_dict(torch.load(optimizer_path, map_location=device))
        if scheduler is not None and scheduler_path.exists():
            scheduler.load_state_dict(torch.load(scheduler_path, map_location=device))
        if state_path.exists():
            return json.loads(state_path.read_text(encoding="utf-8"))
        return {}

    def _save_epoch_checkpoints(
        self,
        output_dir: str | Path,
        epoch: int,
        metrics: dict[str, float],
        checkpoint_config: dict[str, Any],
        optimizer: Any,
        scheduler: Any | None,
        best_score: float | None,
        no_improve_epochs: int,
        improved: bool,
    ) -> None:
        """config.checkpoint 정책에 따라 best/last/epoch checkpoint를 저장합니다."""
        if not checkpoint_config.get("enabled"):
            return
        checkpoint_root = Path(output_dir) / str(checkpoint_config.get("dir", "checkpoints"))
        if checkpoint_config.get("save_last", True):
            self._save_checkpoint(
                checkpoint_root / "last",
                epoch,
                metrics,
                optimizer,
                scheduler,
                best_score,
                no_improve_epochs,
            )
        if checkpoint_config.get("save_best", True) and improved:
            self._save_checkpoint(
                checkpoint_root / "best",
                epoch,
                metrics,
                optimizer,
                scheduler,
                best_score,
                no_improve_epochs,
            )
        if checkpoint_config.get("save_every_epoch"):
            self._save_checkpoint(
                checkpoint_root / f"epoch_{epoch}",
                epoch,
                metrics,
                optimizer,
                scheduler,
                best_score,
                no_improve_epochs,
            )

    def _save_checkpoint(
        self,
        checkpoint_dir: Path,
        epoch: int,
        metrics: dict[str, float],
        optimizer: Any,
        scheduler: Any | None,
        best_score: float | None,
        no_improve_epochs: int,
    ) -> None:
        """HuggingFace weight와 학습 상태를 한 checkpoint 디렉터리에 저장합니다."""
        import torch

        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(checkpoint_dir)
        self.tokenizer.save_pretrained(checkpoint_dir)
        torch.save(optimizer.state_dict(), checkpoint_dir / "optimizer.pt")
        if scheduler is not None:
            torch.save(scheduler.state_dict(), checkpoint_dir / "scheduler.pt")
        state = {
            "epoch": epoch,
            "metrics": metrics,
            "best_score": best_score,
            "no_improve_epochs": no_improve_epochs,
        }
        (checkpoint_dir / "trainer_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

    def predict(self, texts: list[str], batch_size: int = 8) -> list[str]:
        """여러 텍스트에 대한 label 예측을 반환합니다."""
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
            # 평가/예측에서는 gradient를 만들지 않아 메모리 사용을 줄입니다.
            for input_ids, attention_mask in loader:
                outputs = self.model(
                    input_ids=input_ids.to(device),
                    attention_mask=attention_mask.to(device),
                )
                label_ids = outputs.logits.argmax(dim=-1).detach().cpu().tolist()
                predictions.extend(self.id2label[int(label_id)] for label_id in label_ids)
        return predictions

    def predict_one(self, text: str) -> str:
        """단일 텍스트에 대한 label 예측을 반환합니다."""
        return self.predict([text])[0]

    def save(self, output_dir: str | Path) -> None:
        """tokenizer와 model weight를 `hf_model/` 폴더에 저장합니다."""
        model_dir = Path(output_dir) / "hf_model"
        model_dir.mkdir(parents=True, exist_ok=True)
        # HuggingFace 표준 save_pretrained 포맷을 쓰면 from_pretrained로 바로 복원할 수 있습니다.
        self.model.save_pretrained(model_dir)
        self.tokenizer.save_pretrained(model_dir)

    def to_dict(self) -> dict[str, Any]:
        """HuggingFace artifact를 다시 불러오기 위한 metadata를 반환합니다."""
        return {
            "model_type": MODEL_TYPE,
            "base_model_name": self.model_name,
            "model_dir": "hf_model",
            "label2id": self.label2id,
            "id2label": {str(key): value for key, value in self.id2label.items()},
            "max_length": self.max_length,
        }


def build_label_map(rows: list[dict[str, str]], label_col: str = "label") -> dict[str, int]:
    """class_map.json이 없을 때 label 목록으로 deterministic label map을 만듭니다."""
    labels = sorted({row[label_col] for row in rows})
    return {label: index for index, label in enumerate(labels)}


def _build_scheduler(optimizer: Any, scheduler_config: dict[str, Any], epochs: int, steps_per_epoch: int) -> Any | None:
    """config.scheduler 설정으로 HuggingFace scheduler를 생성합니다."""
    if not scheduler_config.get("enabled"):
        return None
    from transformers import get_scheduler

    name = str(scheduler_config.get("name", "linear"))
    total_steps = max(epochs * max(steps_per_epoch, 1), 1)
    warmup_steps = scheduler_config.get("warmup_steps")
    if warmup_steps is None:
        warmup_steps = int(total_steps * float(scheduler_config.get("warmup_ratio", 0.0)))
    return get_scheduler(
        name=name,
        optimizer=optimizer,
        num_warmup_steps=int(warmup_steps),
        num_training_steps=total_steps,
    )


def _is_improved(score: float, best_score: float | None, *, mode: str, min_delta: float) -> bool:
    """monitor metric이 best score를 갱신했는지 판단합니다."""
    if best_score is None:
        return True
    if mode == "min":
        return score < best_score - min_delta
    return score > best_score + min_delta
