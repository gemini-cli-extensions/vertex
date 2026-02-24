"""Tools for analyzing the output of a Data-Driven Optimize job."""

import base64
import difflib
import html
import io
import json
import os
import re
from typing import Any

import matplotlib
from absl import logging

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

from . import storage, utils

BytesIO = io.BytesIO

UCB_TRAIN_KEY = "ucb_train"
FULL_TRAIN_KEY = "full_train"
FULL_TEST_KEY = "full_test"
UCB_TRAIN_SCORE_KEY = "score_" + UCB_TRAIN_KEY
FULL_TRAIN_SCORE_KEY = "score_" + FULL_TRAIN_KEY
FULL_TEST_SCORE_KEY = "score_" + FULL_TEST_KEY

EXPECTED_TEMPLATES_COUNT = 2


def get_best_prompt(output_path: str) -> str:
    """Parses the output files to find the best performing prompt."""
    try:
        best_prompt_data = storage.read_file_from_base(
            output_path, "optimized_results.json"
        )
        return best_prompt_data.get("prompt", "Prompt not found in file.")
    except (FileNotFoundError, RuntimeError) as e:
        raise RuntimeError(
            "Could not retrieve best prompt. Ensure the optimization job completed"
            " successfully and the output directory contains"
            f" 'optimized_results.json'. Original error: {e}"
        ) from e


def get_performance_comparison(output_path: str) -> dict[str, Any]:
    """Compares the initial and best prompts evaluated on the full test set."""
    test_templates = None
    if storage.file_exists_in_base(output_path, "test_templates.json"):
        try:
            test_templates = storage.read_file_from_base(
                output_path, "test_templates.json"
            )
        except (FileNotFoundError, RuntimeError) as e:
            print(
                "Warning: Could not read test_templates.json from"
                f" {output_path}. Comparison will be unavailable. Original error: {e}"
            )

    ucb_templates = None
    if storage.file_exists_in_base(output_path, "templates.json"):
        try:
            ucb_templates = storage.read_file_from_base(
                output_path, "templates.json"
            )
        except (FileNotFoundError, RuntimeError):
            print(
                f"Warning: Could not read templates.json from {output_path}. "
                "Comparison will be unavailable. Original error: {e}"
            )

    initial_prompt = "Not available"
    best_prompt = "Not available"
    initial_full_test_metrics = {}
    best_full_test_metrics = {}
    initial_ucb_metrics = {}
    best_ucb_metrics = {}

    if test_templates and len(test_templates) == EXPECTED_TEMPLATES_COUNT:
        initial_prompt = test_templates[0].get("prompt")
        best_prompt = test_templates[1].get("prompt")
        initial_full_test_metrics = test_templates[0].get("metrics")
        best_full_test_metrics = test_templates[1].get("metrics")

    if ucb_templates:
        # Find initial prompt (step 0)
        for t in ucb_templates:
            if t.get("step") == 0:
                initial_ucb_metrics = t.get("metrics")
                break
        # Find best prompt by prompt text
        for t in ucb_templates:
            if t.get("prompt") == best_prompt:
                best_ucb_metrics = t.get("metrics")
                break

    return {
        "initial_prompt": {
            "prompt": initial_prompt,
            "ucb_metrics": initial_ucb_metrics,
            "full_test_metrics": initial_full_test_metrics,
        },
        "best_prompt": {
            "prompt": best_prompt,
            "ucb_metrics": best_ucb_metrics,
            "full_test_metrics": best_full_test_metrics,
        },
    }


def _load_raw_template_files(output_path: str) -> dict[str, Any]:
    """Loads all relevant template JSON files into a structured dict."""

    def _read_json_if_exists(path, filename):
        try:
            if storage.file_exists_in_base(path, filename):
                logging.info("File %s exists, attempting to read.", filename)
                return storage.read_file_from_base(path, filename)
        except (FileNotFoundError, RuntimeError) as e:
            logging.warning("Failed to read file %s: %s", filename, e)
        return None

    files = {
        UCB_TRAIN_KEY: "templates.json",
        FULL_TRAIN_KEY: "all_candidates_full_train_templates.json",
        FULL_TEST_KEY: "all_candidates_full_test_templates.json",
    }

    data = {}
    for key, template_file in files.items():
        templates = _read_json_if_exists(output_path, template_file)
        if templates:
            data[key] = {"templates": templates}
            logging.info("Read %d templates for %s.", len(templates), key)
    return data


def _infer_metric_name(data_dict: dict[str, Any]) -> str:
    """Infers the metric name from the loaded template data."""
    for key in [UCB_TRAIN_KEY, FULL_TRAIN_KEY, FULL_TEST_KEY]:
        templates = data_dict.get(key, {}).get("templates")
        if templates:
            name = next(
                (
                    k
                    for k in templates[0].get("metrics", {})
                    if k not in ["row_count", "uid"]
                ),
                None,
            )
            if name:
                return name
    raise RuntimeError("Could not determine metric name for ranking.")


def _get_all_metrics_ranked(
    output_path: str,
    use_uid_as_candidate_key: bool = False,
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    """Gets a ranked list of all prompt candidates with detailed info."""
    data = _load_raw_template_files(output_path)
    metric_name = _infer_metric_name(data)
    logging.info("Determined metric name: %s", metric_name)

    # Dict of candidate results & info keyed by candidate_key
    candidates = {}
    # Mapping of candidate_key to full prompt text
    prompts_map = {}
    # Internal mapping: identity -> key, uid -> key
    identity_to_key = {}
    uid_to_key = {}

    def _process_candidate_result(result_set_key: str):
        if result_set_key not in data:
            return

        templates = data[result_set_key]["templates"]
        for template in templates:
            uid = template.get("metrics", {}).get("uid")
            step = template.get("step")
            prompt = template.get("prompt")
            identity = (step, prompt)

            # Map identity or UID to a unique candidate key
            if identity in identity_to_key:
                candidate_key = identity_to_key[identity]
            elif uid and str(uid) in uid_to_key:
                candidate_key = uid_to_key[str(uid)]
            else:
                candidate_key = (
                    str(uid) if uid else f"s{step}_n{len(identity_to_key)}"
                )
                identity_to_key[identity] = candidate_key
                if uid:
                    uid_to_key[str(uid)] = candidate_key

            if candidate_key not in candidates:
                candidates[candidate_key] = {
                    "uid": uid,
                    "step": step,
                    "candidate_key": candidate_key,
                }
                prompts_map[candidate_key] = prompt

            # Back-fill UID if found in subsequent file
            if uid and not candidates[candidate_key]["uid"]:
                candidates[candidate_key]["uid"] = uid
                uid_to_key[str(uid)] = candidate_key

            candidates[candidate_key]["score_" + result_set_key] = template.get(
                "metrics", {}
            ).get(metric_name)

    _process_candidate_result(UCB_TRAIN_KEY)
    _process_candidate_result(FULL_TRAIN_KEY)
    _process_candidate_result(FULL_TEST_KEY)

    if not candidates:
        raise RuntimeError("No candidate data found to rank prompts.")

    candidate_list = list(candidates.values())
    sort_priority = [
        UCB_TRAIN_SCORE_KEY,
        FULL_TRAIN_SCORE_KEY,
        FULL_TEST_SCORE_KEY,
    ]
    sort_key = next(
        (k for k in sort_priority if any(k in c for c in candidate_list)), None
    )

    if not sort_key:
        raise RuntimeError("No valid scores found to rank prompts.")

    sorted_candidates = sorted(
        [c for c in candidate_list if c.get(sort_key) is not None],
        key=lambda x: x[sort_key],
        reverse=True,
    )
    return sorted_candidates, metric_name, prompts_map


def _create_learning_curve_plot(df: pd.DataFrame, metric_name: str) -> str:
    """Generates the learning curve plot as a base64 encoded string."""
    plt.figure(figsize=(12, 7))
    plotted_anything = False

    def _plot_series(score_key, label, marker, linestyle):
        nonlocal plotted_anything
        if score_key in df.columns:
            subset = df.dropna(subset=[score_key, "step"])
            if not subset.empty:
                best_prompts_by_step = subset.loc[
                    subset.groupby("step")[score_key].idxmax()
                ]
                if not best_prompts_by_step.empty:
                    plt.plot(
                        best_prompts_by_step["step"],
                        best_prompts_by_step[score_key],
                        marker=marker,
                        linestyle=linestyle,
                        label=label,
                    )
                    plotted_anything = True

    _plot_series(UCB_TRAIN_SCORE_KEY, "Training Score (Mini-batches)", "o", "-")
    _plot_series(FULL_TRAIN_SCORE_KEY, "Full Training Set Score", "x", "--")
    _plot_series(FULL_TEST_SCORE_KEY, "Full Test Set Score", "s", ":")

    plt.title("Best Prompt Performance Over Optimization Steps")
    plt.xlabel("Optimization Step")
    plt.ylabel(f"Score ({metric_name})")
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
    if plotted_anything:
        plt.legend()
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _render_dict_diff(
    old_dict: dict, new_dict: dict, indent: int = 0
) -> tuple[str, str]:
    """Renders two dicts side-by-side with HTML highlighting for diffs."""
    old_lines = []
    new_lines = []
    indent_str = "  " * indent
    all_keys = sorted(list(set(old_dict.keys()) | set(new_dict.keys())))

    old_lines.append(indent_str + "{")
    new_lines.append(indent_str + "{")

    for key in all_keys:
        key_str = html.escape(json.dumps(key))
        old_val = old_dict.get(key)
        new_val = new_dict.get(key)

        old_exists = key in old_dict
        new_exists = key in new_dict

        val_diff = old_val != new_val
        line_class = (
            "optimizer_diff_chg"
            if val_diff or not old_exists or not new_exists
            else ""
        )

        o_line = f"{indent_str}  {key_str}: "
        n_line = f"{indent_str}  {key_str}: "

        if not new_exists:
            o_line += html.escape(json.dumps(old_val))
            n_line += ""
            line_class = "optimizer_diff_sub"
        elif not old_exists:
            o_line += ""
            n_line += html.escape(json.dumps(new_val))
            line_class = "optimizer_diff_add"
        elif isinstance(old_val, dict) and isinstance(new_val, dict):
            o_s, n_s = _render_dict_diff(old_val, new_val, indent + 1)
            o_line = f"{indent_str}  {key_str}:\n{o_s}"
            n_line = f"{indent_str}  {key_str}:\n{n_s}"
        elif isinstance(old_val, list) and isinstance(new_val, list):
            if old_val == new_val:
                o_line += html.escape(json.dumps(old_val))
                n_line += html.escape(json.dumps(new_val))
            else:
                o_line += f"{html.escape(json.dumps(old_val))}"
                n_line += f"{html.escape(json.dumps(new_val))}"
        else:  # Primitive types
            o_line += html.escape(json.dumps(old_val))
            n_line += html.escape(json.dumps(new_val))

        if line_class:
            old_lines.append(f'<span class="{line_class}">{o_line}</span>')
            new_lines.append(f'<span class="{line_class}">{n_line}</span>')
        else:
            old_lines.append(o_line)
            new_lines.append(n_line)

    old_lines.append(indent_str + "}")
    new_lines.append(indent_str + "}")
    return "\n".join(old_lines), "\n".join(new_lines)


def _format_value(value):
    if isinstance(value, float):
        return f"{value:.4f}"
    return value if value is not None else "N/A"


def _load_analysis_data(analysis_data_path: str) -> dict[str, Any]:
    """Loads and re-joins split analysis data files."""
    try:
        with open(analysis_data_path) as f:
            analysis_data = json.load(f)

        # Load split files
        metrics_path = analysis_data_path.replace(".json", "_metrics.json")
        prompts_path = analysis_data_path.replace(".json", "_prompts.json")

        if os.path.exists(metrics_path):
            with open(metrics_path) as f:
                analysis_data["all_metrics_ranked"] = json.load(f)

        if not os.path.exists(prompts_path):
            return analysis_data

        with open(prompts_path) as f:
            prompts_map = json.load(f)

        # Re-join prompts into all_metrics_ranked
        for p in analysis_data.get("all_metrics_ranked", []):
            ck = p.get("candidate_key")
            if ck in prompts_map:
                p["prompt"] = prompts_map[ck]

        # Re-join prompts into comparison section
        comp = analysis_data.get("comparison", {})
        for key in ["initial_prompt", "best_prompt"]:
            target = comp.get(key)
            if isinstance(target, dict):
                # Use UID from full_test_metrics to find the prompt
                uid = target.get("full_test_metrics", {}).get("uid")
                if uid and str(uid) in prompts_map:
                    target["prompt"] = prompts_map[str(uid)]

        return analysis_data
    except Exception as e:
        raise RuntimeError(
            f"Failed to load analysis data from {analysis_data_path}: {e}"
        ) from e


def _render_config_section(
    config: dict[str, Any], suggested_config_data: dict[str, Any] | None
) -> str:
    """Renders the HTML section for the run configuration and suggestions."""
    base_config = config or {}
    rationale_html = ""
    modifications_html = ""

    if suggested_config_data:
        modifications = suggested_config_data.get("suggested_config", {})
        merged_config = utils.merge_configs(base_config, modifications)

        if "rationale" in suggested_config_data:
            rationale_html = f"""
        <h3>Rationale for Suggested Modifications:</h3>
        <p>{suggested_config_data['rationale']}</p>
      """

        if modifications:
            modifications_html = "<h3>Summary of Suggested Changes:</h3><ul>"
            for key, value in modifications.items():
                modifications_html += f"<li><b>{key}:</b> {value}</li>"
            modifications_html += "</ul>"

        old_config_html, new_config_html = _render_dict_diff(
            base_config, merged_config
        )

        config_display_html = f"""
      {modifications_html}
      <div style="display: flex;">
          <div style="flex: 1; padding-right: 10px;">
              <h3>Current Run Config:</h3>
              <pre class="optimizer-pre">{old_config_html}</pre>
          </div>
          <div style="flex: 1; padding-left: 10px;">
              <h3>Config for Next Run (Changes Highlighted):</h3>
              <pre class="optimizer-pre">{new_config_html}</pre>
          </div>
      </div>
    """
    else:
        base_config_str = json.dumps(base_config, indent=2)
        config_display_html = f"""
      <div style="display: flex;">
          <div style="flex: 1; padding-right: 10px;">
              <h3>Current Run Config:</h3>
              <pre class="optimizer-pre">{base_config_str}</pre>
          </div>
          <div style="flex: 1; padding-left: 10px;">
              <h3>Config for Next Run:</h3>
              <p>No suggested modifications provided.</p>
          </div>
      </div>
    """

    return f"""
        <div class="card">
            <h2>Run Configuration</h2>
            {rationale_html}
            {config_display_html}
        </div>
    """


def _render_comparison_section(comparison: dict[str, Any] | None) -> str:
    """Renders the HTML section for the performance comparison."""
    if not comparison:
        comparison_html = (
            '<p class="error">Prompt comparison data is not available.</p>'
        )
    elif "error" in comparison:
        comparison_html = f'<p class="error">Prompt comparison failed: {comparison["error"]}</p>'
    else:
        initial_prompt_str = comparison.get("initial_prompt", {}).get(
            "prompt", "N/A"
        )
        best_prompt_str = comparison.get("best_prompt", {}).get("prompt", "N/A")
        a_words = re.split(r"(\s+)", initial_prompt_str)
        b_words = re.split(r"(\s+)", best_prompt_str)
        s = difflib.SequenceMatcher(None, a_words, b_words, autojunk=False)
        a_out, b_out = [], []
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            a_segment = "".join(a_words[i1:i2])
            b_segment = "".join(b_words[j1:j2])

            a_segment_html = a_segment.replace("\n", "<br>")
            b_segment_html = b_segment.replace("\n", "<br>")

            if tag == "replace":
                a_out.append(f'<span class="diff_chg">{a_segment_html}</span>')
                b_out.append(f'<span class="diff_chg">{b_segment_html}</span>')
            elif tag == "delete":
                a_out.append(f'<span class="diff_sub">{a_segment_html}</span>')
            elif tag == "insert":
                b_out.append(f'<span class="diff_add">{b_segment_html}</span>')
            elif tag == "equal":
                a_out.append(a_segment_html)
                b_out.append(b_segment_html)

        initial_prompt_html = "".join(a_out)
        best_prompt_html = "".join(b_out)
        diff = f"""
        <table class="diff">
             <tr>
                <td class="diff_header" width="50%">Initial Prompt</td>
                <td class="diff_header" width="50%">Best Prompt</td>
            </tr>
            <tr>
                <td class="prompt">{initial_prompt_html}</td>
                <td class="prompt">{best_prompt_html}</td>
            </tr>
        </table>
    """

        def _render_metrics_table(metrics_dict):
            html_str = '<td><table style="border: none;">'
            if isinstance(metrics_dict, dict):
                for key, value in metrics_dict.items():
                    html_str += (
                        "<tr><td"
                        f' style="border: none;"><b>{key}</b></td><td style="border:'
                        f' none;">{_format_value(value)}</td></tr>'
                    )
            else:
                html_str += '<tr><td style="border: none;">N/A</td></tr>'
            html_str += "</table></td>"
            return html_str

        initial_full_test_metrics_html = _render_metrics_table(
            comparison.get("initial_prompt", {}).get("full_test_metrics", "N/A")
        )
        best_full_test_metrics_html = _render_metrics_table(
            comparison.get("best_prompt", {}).get("full_test_metrics", "N/A")
        )
        initial_ucb_metrics_html = _render_metrics_table(
            comparison.get("initial_prompt", {}).get("ucb_metrics", "N/A")
        )
        best_ucb_metrics_html = _render_metrics_table(
            comparison.get("best_prompt", {}).get("ucb_metrics", "N/A")
        )

        comparison_html = f"""
        <h4>Metrics</h4>
        <table>
            <tr>
                <th></th>
                <th>Initial Prompt</th>
                <th>Best Prompt</th>
            </tr>
            <tr>
                <td><strong>Training Metrics (Mini-batches)</strong></td>
                {initial_ucb_metrics_html}
                {best_ucb_metrics_html}
            </tr>
            <tr>
                <td><strong>Full Test Set Metrics</strong></td>
                {initial_full_test_metrics_html}
                {best_full_test_metrics_html}
            </tr>
        </table>
        <h4>Prompt Comparison</h4>
        {diff}
    """

    return f"""
        <div class="card">
            <h2>Performance Comparison</h2>
            {comparison_html}
        </div>
    """


def _render_top_prompts_section(
    all_metrics_ranked: list[dict[str, Any]],
    top_n_prompts: int,
    metric_source: str | None,
    metric_name: str | None,
) -> str:
    """Renders the HTML section for the top ranked prompts."""
    if not all_metrics_ranked:
        return ""

    ranking_info = ""
    if metric_source and metric_name:
        src_label = metric_source.replace(
            "ucb_train", "Training (Mini-batches)"
        )
        ranking_info = (
            f"<p><i>Ranked by {src_label} Score on metric {metric_name}</i></p>"
        )

    rows = []
    for p in all_metrics_ranked[:top_n_prompts]:
        prompt_html = p.get("prompt", "N/A").replace("\n", "<br>")
        rows.append(
            f"""<tr>
                <td>{p.get('step', 'N/A')}</td>
                {'<td>' + _format_value(p.get(UCB_TRAIN_SCORE_KEY)) + '</td>' if UCB_TRAIN_SCORE_KEY in p else ''}
                {'<td>' + _format_value(p.get(FULL_TRAIN_SCORE_KEY)) + '</td>' if FULL_TRAIN_SCORE_KEY in p else ''}
                {'<td>' + _format_value(p.get(FULL_TEST_SCORE_KEY)) + '</td>' if FULL_TEST_SCORE_KEY in p else ''}
                <td><div class='prompt scrollable-prompt'>{prompt_html}</div></td>
            </tr>"""
        )

    return f"""
        <div class="card">
            <h2>Top {top_n_prompts} Ranked Prompts</h2>
            {ranking_info}
            <table>
                <tr>
                    <th>Step</th>
                    {"<th>Training Score (Mini-batches)</th>" if UCB_TRAIN_SCORE_KEY in all_metrics_ranked[0] else ""}
                    {"<th>Train Score (Full)</th>" if FULL_TRAIN_SCORE_KEY in all_metrics_ranked[0] else ""}
                    {"<th>Test Score (Full)</th>" if FULL_TEST_SCORE_KEY in all_metrics_ranked[0] else ""}
                    <th>Prompt</th>
                </tr>
                {''.join(rows)}
            </table>
        </div>
    """


def generate_report(
    analysis_data: dict[str, Any] | None = None,
    report_path: str = "data_driven_optimize_analysis_report.html",
    suggested_config_data: dict[str, Any] | None = None,
    top_n_prompts: int = 10,
    analysis_data_path: str | None = None,
) -> None:
    """Generates a comprehensive HTML report from Data-Driven Optimize analysis results."""
    if analysis_data_path:
        analysis_data = _load_analysis_data(analysis_data_path)

    if not analysis_data:
        raise ValueError(
            "Either analysis_data or analysis_data_path must be provided."
        )

    config = analysis_data.get("config")
    comparison = analysis_data.get("comparison")
    all_metrics_ranked = analysis_data.get("all_metrics_ranked")
    metric_source = analysis_data.get("metric_source")
    metric_name = analysis_data.get("metric_name")

    # 1. Learning Curve Plot
    plot_html = "<p>Not enough data to generate a learning curve plot.</p>"
    if all_metrics_ranked and metric_name:
        try:
            df = pd.DataFrame(all_metrics_ranked)
            plot_b64 = _create_learning_curve_plot(df, metric_name)
            plot_html = f'<img src="data:image/png;base64,{plot_b64}" alt="Learning Curve">'
        except Exception as e:  # pylint: disable=broad-except
            plot_html = f"<p>Couldn't plot learning curve: {e}</p>"

    # 2. Render Sections
    comparison_section = _render_comparison_section(comparison)
    top_prompts_section = (
        _render_top_prompts_section(
            all_metrics_ranked, top_n_prompts, metric_source, metric_name
        )
        if all_metrics_ranked
        else ""
    )
    config_section = (
        _render_config_section(config, suggested_config_data) if config else ""
    )

    main_html = f"""
    <html>
    <head>
        <title>Data-Driven Optimize Analysis Report</title>
        <style>
            body {{ font-family: sans-serif; margin: 2em; }}
            h1, h2, h3, h4 {{ color: #333; }}
            .card {{ border: 1px solid #ddd; border-radius: 5px; padding: 1em; margin-bottom: 1em; }}
            .prompt {{ font-family: monospace; background-color: #f5f5f5; padding: 0.5em; border-radius: 3px; white-space: pre-wrap; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .suggestion {{ background-color: #e7f3ff; border-left: 5px solid #2196F3; padding: 10px; margin-top: 10px; }}
            .error {{ color: #D8000C; background-color: #FFBABA; padding: 10px; }}
            table.diff {{font-family:monospace; border:medium;}}
            .diff_header {{background-color:#e0e0e0}}
            .diff_next {{background-color:#c0c0c0}}
            .diff_add {{background-color:#aaffaa}}
            .diff_chg {{background-color:#ffff77}}
            .diff_sub {{background-color:#ffaaaa}}
            .scrollable-prompt {{ max-height: 200px; overflow-y: auto; display: block; }}
            .optimizer-pre {{ white-space: pre-wrap; word-wrap: break-word; }}
            .optimizer_diff_chg {{ background-color: #ffff77; display: block; }}
            .optimizer_diff_add {{ background-color: #aaffaa; display: block; }}
            .optimizer_diff_sub {{ background-color: #ffaaaa; display: block; }}
        </style>
    </head>
    <body>
        <h1>Data-Driven Optimize Analysis Report</h1>
        {comparison_section}
        <div class="card">
            <h2>Learning Curve</h2>
            {plot_html}
        </div>
        {top_prompts_section}
        {config_section}
    </body>
    </html>
    """
    if report_path.startswith("gs://"):
        storage.write_gcs_file(report_path, main_html)
    else:
        with open(report_path, "w") as f:
            f.write(main_html)


def analyze_results(
    output_path: str,
    analysis_data_path: str,
    top_n_prompts: int = 10,
) -> dict[str, Any]:
    """Analyzes results and saves the detailed data to files."""

    def _read_json_if_exists(path, filename):
        if storage.file_exists_in_base(path, filename):
            try:
                return storage.read_file_from_base(path, filename)
            except (FileNotFoundError, RuntimeError):
                return None
        return None

    config = _read_json_if_exists(output_path, "config.json")

    try:
        best_prompt_text = get_best_prompt(output_path)
    except RuntimeError as e:
        best_prompt_text = f"Error: Could not retrieve best prompt: {e}"

    comparison: dict[str, Any] = {}
    try:
        comparison = get_performance_comparison(output_path)
    except (RuntimeError, ValueError) as e:
        comparison = {
            "error": (
                f"Could not retrieve initial v.s. best performance comparison: {e}"
            )
        }

    all_metrics_ranked, metric_name, prompts_map = [], "", {}
    try:
        all_metrics_ranked, metric_name, prompts_map = _get_all_metrics_ranked(
            output_path
        )
    except RuntimeError as e:
        logging.info("Could not retrieve ranked prompts: %s", e)

    full_analysis_data = {
        "config": config,
        "best_prompt": best_prompt_text,
        "comparison": comparison,
        "metric_name": metric_name,
        "metric_source": UCB_TRAIN_KEY,
    }

    # Define split file paths
    metrics_path = analysis_data_path.replace(".json", "_metrics.json")
    prompts_path = analysis_data_path.replace(".json", "_prompts.json")

    try:
        # Save core metadata
        with open(analysis_data_path, "w") as f:
            json.dump(full_analysis_data, f)
        logging.info("Saved core analysis data to %s", analysis_data_path)

        # Save detailed metrics (all_metrics_ranked WITHOUT prompt text)
        with open(metrics_path, "w") as f:
            json.dump(all_metrics_ranked, f)
        logging.info("Saved metrics to %s", metrics_path)

        relevant_keys = set()
        for p in all_metrics_ranked[:top_n_prompts]:
            relevant_keys.add(p.get("candidate_key"))

        # Add comparison prompts
        if comparison and isinstance(comparison, dict):
            for key in ["initial_prompt", "best_prompt"]:
                prompt_data = comparison.get(key)
                if isinstance(prompt_data, dict):
                    metrics = prompt_data.get("full_test_metrics")
                    if isinstance(metrics, dict):
                        uid = metrics.get("uid")
                        if uid:
                            relevant_keys.add(str(uid))

        filtered_prompts_map = {
            k: v for k, v in prompts_map.items() if k in relevant_keys
        }

        with open(prompts_path, "w") as f:
            json.dump(filtered_prompts_map, f)
        logging.info(
            "Saved %d prompts to %s", len(filtered_prompts_map), prompts_path
        )
    except Exception as e:
        logging.error("Failed to save analysis data: %s", e)

    # Create a copy of all_metrics_ranked without prompt text for the summary.
    summary_metrics = []
    for p in all_metrics_ranked:
        p_copy = p.copy()
        p_copy.pop("prompt", None)
        summary_metrics.append(p_copy)

    return {
        "message": (
            f"Analysis complete. Full results saved to {analysis_data_path}"
        ),
        "analysis_data_path": analysis_data_path,
        "metrics_path": metrics_path,
        "prompts_path": prompts_path,
        "best_prompt": best_prompt_text,
        "all_metrics_ranked": summary_metrics,
        "config_summary": {
            "project": config.get("project") if config else "N/A",
            "target_model": config.get("target_model") if config else "N/A",
            "eval_metrics": config.get("eval_metrics_types")
            if config
            else "N/A",
            "num_steps": config.get("num_steps") if config else "N/A",
        },
        "best_prompt_score": (
            comparison.get("best_prompt", {})
            .get("full_test_metrics", {})
            .get(metric_name)
            if (
                isinstance(comparison, dict)
                and isinstance(comparison.get("best_prompt"), dict)
                and isinstance(
                    comparison["best_prompt"].get("full_test_metrics"), dict
                )
            )
            else "N/A"
        ),
        "total_candidates": len(all_metrics_ranked),
    }
