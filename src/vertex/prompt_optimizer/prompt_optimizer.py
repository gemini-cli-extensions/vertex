"""Tools for Vertex AI Prompt Optimizer."""

import json
from typing import Any

import vertexai
from google.cloud import storage
from vertexai._genai import Client

from . import storage as storage_utils
from . import utils


class PromptOptimizer:
    def __init__(self, project: str, location: str):
        """Initializes the Vertex AI client and accesses the prompt_optimizer."""
        try:
            vertexai.init(project=project, location=location)
            self.client = Client(project=project, location=location)
            self.storage_client = storage.Client(project=project)
            self.project = project
            self.location = location
            print(
                "Initialized Vertex AI and Storage Clients for project:"
                f" {project}, location: {location}"
            )
        except Exception as e:
            print(
                "Error initializing Google Cloud Clients. Ensure gcloud is"
                f" authenticated and APIs are enabled: {e}\n"
            )

            self.client = None
            self.optimizer = None
            self.storage_client = None
            self.project = None
            self.location = "us-central1"

    def write_config(
        self,
        gcs_config_uri: str,
        prompt_optimizer_method: str,
        target_model_endpoint_url: str | None = None,
        base_config: dict[str, Any] | None = None,
        modifications: dict[str, Any] | None = None,
        base_config_path: str | None = None,
    ) -> str:
        """Constructs a JSON configuration for Data-Driven Optimize and uploads it to GCS.

        This tool generates a JSON configuration file based on the provided
        parameters and uploads it to the specified Google Cloud Storage URI. This
        configuration file is required to run data-driven prompt optimization.

        Args:
          gcs_config_uri: The GCS URI where the generated VAPO config JSON file will
            be saved (e.g., 'gs://my-bucket/vapo/config.json').
          prompt_optimizer_method: The method for prompt optimization. Either
            'VAPO' or 'OPTIMIZATION_TARGET_GEMINI_NANO'.
          target_model_endpoint_url: The custom endpoint URL for the target model.
            Required for Gemini Nano target.
          base_config: Optional. A dictionary representing the base configuration.
          modifications: Optional. A dictionary representing the modifications to
            apply to the base config.
          base_config_path: Optional. Path to a base config file. If provided and
            `base_config` is None, this config will be loaded.

        Returns:
          A string containing a success message and details about the uploaded
          configuration file, including a link to the Vertex AI console.
        """
        if not self.storage_client:
            raise ValueError("Google Cloud Storage client not initialized.")
        if not gcs_config_uri.startswith(
            "gs://"
        ) or not gcs_config_uri.endswith(".json"):
            raise ValueError(
                "Error: `gcs_config_uri` must be a valid GCS URI ending in .json."
            )

        config_dict = {}
        if base_config:
            config_dict = base_config.copy()
        elif base_config_path:
            try:
                base_bucket_name, base_object_name = base_config_path[5:].split(
                    "/", 1
                )
                base_bucket = self.storage_client.get_bucket(base_bucket_name)
                base_blob = base_bucket.blob(base_object_name)
                config_dict = json.loads(base_blob.download_as_string())
            except Exception as e:
                raise RuntimeError(
                    f"Error reading base config from {base_config_path}: {e}"
                ) from e

        if modifications:
            config_dict = utils.merge_configs(config_dict, modifications)

        # Ensure tool-level parameters don't leak into the config file.
        config_dict.pop("prompt_optimizer_method", None)

        if prompt_optimizer_method == "VAPO":
            # Remove parameters not supported by VAPO in the config file yet.
            config_dict.pop("batch_size", None)
            config_dict.pop("target_model_endpoint_url", None)

        if target_model_endpoint_url and prompt_optimizer_method != "VAPO":
            config_dict["target_model_endpoint_url"] = target_model_endpoint_url

        # Automatically generate demo_and_query_template if missing
        if "demo_and_query_template" not in config_dict:
            data_vars = config_dict.get("data_vars", [])
            label_var = config_dict.get("label_variable")
            if data_vars and label_var:
                input_vars = [v for v in data_vars if v != label_var]
                template_parts = []
                for v in input_vars:
                    template_parts.append(f"{v.capitalize()}: {{{{{v}}}}}")
                template_parts.append(
                    f"{label_var.capitalize()}: {{{{{label_var}}}}}"
                )
                config_dict["demo_and_query_template"] = "\n".join(
                    template_parts
                )

        try:
            bucket_name, object_name = gcs_config_uri[5:].split("/", 1)
            json_str = json.dumps(config_dict, indent=2)
            bucket = self.storage_client.get_bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.upload_from_string(json_str, content_type="application/json")
            return (
                "Successfully created and uploaded configuration to:"
                f" {gcs_config_uri}\n\n"
                f"Remember to ensure the service account running the Vertex AI job"
                f" has necessary permissions "
                f"to access GCS (`input_data_path`, `output_path`) and Vertex AI."
            )
        except Exception as e:
            raise RuntimeError(
                f"Error creating or uploading configuration to GCS: {e}"
            ) from e

    def run_data_driven_optimize(
        self,
        config_gcs_path: str,
        service_account: str,
        prompt_optimizer_method: str,
        wait_for_completion: bool = False,
    ) -> str:
        """Starts a data-driven prompt optimization job on Vertex AI.

        This method uses a dataset and configurable metrics. The `config_gcs_path`
        must point to a JSON file in Google Cloud Storage.

        Args:
          config_gcs_path: The Google Cloud Storage URI (e.g.,
            "gs://your-bucket/config.json") to a JSON file containing the Prompt
            Optimizer configuration. This is required.
          service_account: The service account email to run the job. This is
            required.
          prompt_optimizer_method: The method for prompt optimization. Either
            'VAPO' or 'OPTIMIZATION_TARGET_GEMINI_NANO'.
          wait_for_completion: If True, the tool will block until the Vertex AI
            CustomJob completes. Defaults to False.

        Returns:
          A string indicating the status and details of the optimization job,
          including a link to the Vertex AI console.
        """
        if not self.client:
            raise ValueError(
                "Vertex AI client not initialized. Please check your setup (gcloud"
                " auth, project/location)."
            )
        if not config_gcs_path.startswith(
            "gs://"
        ) or not config_gcs_path.endswith(".json"):
            raise ValueError(
                "Error: config_gcs_path must be a valid GCS URI to a JSON file"
                " (e.g., 'gs://your-bucket/config.json')."
            )

        # Set the optimizer method based on user choice
        try:
            optimizer_method = getattr(
                vertexai.types.PromptOptimizerMethod, prompt_optimizer_method
            )
        except AttributeError:
            raise ValueError(
                f"Invalid prompt_optimizer_method: {prompt_optimizer_method}. Must be"
                " 'VAPO' or 'OPTIMIZATION_TARGET_GEMINI_NANO'."
            )

        vapo_config = {
            "config_path": config_gcs_path,
            "service_account": service_account,
            "wait_for_completion": wait_for_completion,
        }

        try:
            # Using the new launch_optimization_job method in the prompts module
            job = self.client.prompts.launch_optimization_job(
                method=optimizer_method,
                config=vapo_config,
            )
            # Deprecated method for reference:
            # job = self.client.prompt_optimizer.optimize(
            #     method=optimizer_method,
            #     config=vapo_config,
            # )
            job_id = job.name.split("/")[-1] if job.name else "N/A"
            dashboard_url = f"https://console.cloud.google.com/vertex-ai/locations/{self.location}/training/{job_id}/cpu?project={self.project}"
            response_msg = "--- Data-Driven Optimization Job Started via Vertex AI SDK ---\n"
            response_msg += f"Vertex AI CustomJob Name: {job.name}\n"
            response_msg += f"Job ID: {job_id}\n"
            response_msg += f"Current State: {job.state.name}\n"
            response_msg += f"View job status and logs at: {dashboard_url}\n"
            if wait_for_completion:
                response_msg += "\nWaiting for job to complete...\n"
                response_msg += f"Job finished with state: {job.state.name}\n"
            else:
                response_msg += (
                    "\nJob is running in the background. Check the provided URL for"
                    " progress.\n"
                )
            return response_msg
        except ValueError as ve:
            raise ValueError(f"Configuration Error: {ve}") from ve
        except RuntimeError as re:
            raise RuntimeError(
                f"Job Execution Error: {re}. Check Vertex AI logs for details."
            ) from re
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred: {e}") from e

    def run_few_shot_optimization(
        self,
        prompt_to_optimize: str,
        example_path: str,
        method: str,
    ) -> str:
        """Applies few shot prompt optimization to a prompt using user provided dataset and method.

        Args:
            prompt_to_optimize: The zero-based index of the prompt to improve.
            example_path: GCS path to the csv file containg few-shot examples
            method: The optimization method to use for few shot prompt improvement. The
                method should be one of the following:
                - TARGET_RESPONSE: Optimize the prompt to match the target response.
                - RUBRICS: Optimize the prompt to improve the rubrics scores.

        Returns:
            Optimized prompt.
        """
        if not self.client:
            raise ValueError(
                "Error: Client was not initialized properly. Try authenticating then rerunning"
            )

        example_df = storage_utils._read_csv_from_gcs(example_path)
        optimization_target = utils._get_optimization_target(method)
        config = vertexai.types.OptimizeConfig(
            optimization_target=optimization_target,
            examples_dataframe=example_df,
        )
        response = self.client.prompts.optimize(
            prompt=prompt_to_optimize,
            config=config,
        )
        return response.parsed_response.suggested_prompt
