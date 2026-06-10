from __future__ import annotations

from pathlib import Path

from src.predict import predict_one


def infer_image(
    image_path: str,
    config_path: str = "configs/smoke/smoke_test.yaml",
    project_root: str = ".",
) -> dict[str, str]:
    """향후 FastAPI 데모에서 재사용할 작은 추론 연결 지점."""
    prediction = predict_one(config_path, project_root, image_path)
    return {"image_path": str(Path(image_path)), "prediction": prediction}


if __name__ == "__main__":
    print(infer_image("data/processed/images/red_000.ppm"))
