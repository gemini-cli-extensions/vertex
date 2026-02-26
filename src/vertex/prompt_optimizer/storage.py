"""Utility functions for reading from and writing to GCS or local paths."""

import io
import json
from pathlib import Path
from typing import Any

import pandas as pd
from google.cloud import storage

EXPECTED_GCS_PARTS = 2


def _parse_gcs_uri(gcs_uri: str) -> tuple[str, str]:
    """Parses a GCS URI into bucket and object names."""
    if not gcs_uri.startswith("gs://"):
        raise ValueError("Invalid GCS URI. Must start with 'gs://'.")
    parts = gcs_uri[5:].split("/", 1)
    if len(parts) != EXPECTED_GCS_PARTS:
        raise ValueError(
            "Invalid GCS URI format. Expected 'gs://bucket/object'."
        )
    return parts[0], parts[1]


def _read_json_from_gcs(gcs_uri: str) -> Any:
    """Reads and parses a JSON file from GCS."""
    try:
        storage_client = storage.Client()
        bucket_name, blob_name = _parse_gcs_uri(gcs_uri)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return json.loads(blob.download_as_string())
    except Exception as e:
        raise RuntimeError(f"Failed to read from GCS URI {gcs_uri}: {e}") from e


def _read_csv_from_gcs(path: str) -> pd.DataFrame:
    if not _is_gcs_path(path) or not path.endswith(".csv"):
        raise ValueError(
            "Few-shot examples must be stored as CSV file in a GCS bucket, ",
            f"but `{path}` was provided",
        )
    try:
        storage_client = storage.Client()
        bucket_name, blob_name = _parse_gcs_uri(path)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        csv_bytes = blob.download_as_bytes()
        return pd.read_csv(io.BytesIO(csv_bytes))
    except Exception as e:
        raise RuntimeError(f"Failed to read from GCS URI {path}: {e}") from e


def _write_json_to_gcs(data: Any, gcs_uri: str):
    """Writes a JSON object to a GCS file."""
    storage_client = storage.Client()
    bucket_name, blob_name = _parse_gcs_uri(gcs_uri)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(json.dumps(data, indent=2), "application/json")


def write_gcs_file(gcs_uri: str, content: str, content_type: str = "text/html"):
    """Writes string content to a GCS file."""
    storage_client = storage.Client()
    bucket_name, blob_name = _parse_gcs_uri(gcs_uri)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(content, content_type)


def _is_gcs_path(path: str) -> bool:
    """Checks if a path is a GCS URI."""
    return path.startswith("gs://")


def read_file_from_base(base_path: str, file_name: str) -> Any:
    """Reads a JSON file from a local or GCS base path."""
    if _is_gcs_path(base_path):
        file_path = f"{base_path.rstrip('/')}/{file_name}"
        return _read_json_from_gcs(file_path)
    else:
        file_path = str(Path(base_path) / file_name)
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found at {file_path}")
        with open(file_path) as f:
            return json.load(f)


def file_exists_in_base(base_path: str, file_name: str) -> bool:
    """Checks if a file exists in a local or GCS base path."""
    if _is_gcs_path(base_path):
        file_path = f"{base_path.rstrip('/')}/{file_name}"
        storage_client = storage.Client()
        bucket_name, blob_name = _parse_gcs_uri(file_path)
        bucket = storage_client.bucket(bucket_name)
        return storage.Blob(bucket=bucket, name=blob_name).exists()
    else:
        file_path = str(Path(base_path) / file_name)
        return Path(file_path).exists()
