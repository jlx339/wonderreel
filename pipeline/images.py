"""
Image generation — one illustrated scene image per script scene.
Providers: replicate (API, cheap) | comfyui (local, free) | runninghub (cloud ComfyUI, free tier)
"""

import os
import time
import requests
from pathlib import Path

import replicate


def generate_images(scenes, run_dir: Path, config: dict) -> list[Path]:
    """Returns a list of image file paths in scene order."""
    provider = config["images"]["provider"]
    style_prefix = config["images"]["style_prefix"]
    images_dir = run_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    image_paths = []
    for scene in scenes:
        out_path = images_dir / f"scene_{scene.id:02d}.png"

        # Resume from checkpoint if already generated
        if out_path.exists():
            print(f"  [images] scene {scene.id} — using cached image")
            image_paths.append(out_path)
            continue

        full_prompt = f"{style_prefix}, {scene.image_prompt}"
        print(f"  [images] scene {scene.id} — generating...")

        if provider == "replicate":
            _generate_replicate(full_prompt, out_path, config["images"])
        elif provider == "comfyui":
            _generate_comfyui(full_prompt, out_path, config["images"])
        elif provider == "runninghub":
            _generate_runninghub(full_prompt, out_path, config["images"])
        else:
            raise ValueError(f"Unknown image provider: {provider}")

        image_paths.append(out_path)
        time.sleep(0.5)  # Gentle rate limiting

    return image_paths


def _generate_replicate(prompt: str, out_path: Path, cfg: dict):
    output = replicate.run(
        cfg["replicate_model"],
        input={
            "prompt": prompt,
            "width": cfg["width"],
            "height": cfg["height"],
            "num_steps": cfg.get("num_inference_steps", 4),
            "output_format": "png",
        },
    )
    # Replicate returns a URL or file-like object depending on model
    if hasattr(output, "read"):
        out_path.write_bytes(output.read())
    else:
        url = output[0] if isinstance(output, list) else str(output)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        out_path.write_bytes(response.content)


def _generate_comfyui(prompt: str, out_path: Path, cfg: dict):
    """
    Calls a locally running ComfyUI server via its API.
    ComfyUI must be running at cfg['comfyui_url'] before pipeline starts.
    Supports any KSampler-compatible checkpoint (SD 1.5, SDXL, Illustrious, etc.).
    """
    import uuid

    base_url = cfg["comfyui_url"]
    client_id = str(uuid.uuid4())

    checkpoint = cfg.get("comfyui_checkpoint", "animayhemPaleRider_v30PlainsDrifter.safetensors")
    steps = cfg.get("num_inference_steps", 20)
    cfg_scale = cfg.get("cfg_scale", 7.0)
    sampler = cfg.get("sampler_name", "euler_ancestral")
    scheduler = cfg.get("scheduler", "karras")
    negative = cfg.get("negative_prompt", "text, words, letters, watermark, ugly, blurry, deformed")

    workflow = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["4", 1]},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["4", 0],
                "positive": ["1", 0],
                "negative": ["2", 0],
                "latent_image": ["5", 0],
                "seed": 42,
                "steps": steps,
                "cfg": cfg_scale,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0,
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": cfg["width"], "height": cfg["height"], "batch_size": 1},
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"images": ["6", 0], "filename_prefix": "wonderreel"},
        },
    }

    # Queue prompt
    payload = {"prompt": workflow, "client_id": client_id}
    resp = requests.post(f"{base_url}/prompt", json=payload, timeout=10)
    resp.raise_for_status()
    prompt_id = resp.json()["prompt_id"]

    # Poll for completion (max 5 minutes)
    max_retries = 150
    for _ in range(max_retries):
        history = requests.get(f"{base_url}/history/{prompt_id}", timeout=10).json()
        if prompt_id in history:
            entry = history[prompt_id]
            status = entry.get("status", {})

            if status.get("status_str") == "error":
                # Extract the execution_error message if present
                for msg_type, msg_data in status.get("messages", []):
                    if msg_type == "execution_error":
                        raise RuntimeError(
                            f"ComfyUI execution error on node '{msg_data.get('node_type')}': "
                            f"{msg_data.get('exception_message', 'unknown error')}"
                        )
                raise RuntimeError("ComfyUI workflow failed with unknown error.")

            outputs = entry.get("outputs", {})
            if not outputs:
                time.sleep(2)
                continue

            image_info = next(iter(outputs.values()))["images"][0]
            img_url = f"{base_url}/view?filename={image_info['filename']}&subfolder={image_info['subfolder']}&type=output"
            img_data = requests.get(img_url, timeout=30).content
            out_path.write_bytes(img_data)
            return
        time.sleep(2)
    raise TimeoutError(f"ComfyUI did not complete generation for prompt_id={prompt_id} within 5 minutes.")


def _generate_runninghub(prompt: str, out_path: Path, cfg: dict):
    """
    Runs a ComfyUI workflow on RunningHub's cloud platform.

    Requires in cfg:
      - runninghub_api_key   (or RUNNINGHUB_API_KEY env var)
      - runninghub_workflow_id  — the workflow ID from runninghub.ai
      - runninghub_prompt_node_id — ComfyUI node ID that accepts the text prompt
      - runninghub_prompt_field  — field name on that node (default: "text")

    Free tier includes daily credits; FLUX.1 Kontext [dev] is unlimited free.
    """
    import os

    api_key = cfg.get("runninghub_api_key") or os.environ.get("RUNNINGHUB_API_KEY")
    if not api_key:
        raise ValueError("RunningHub API key not set. Add RUNNINGHUB_API_KEY to .env or runninghub_api_key to config.")

    workflow_id = cfg["runninghub_workflow_id"]
    node_id = str(cfg.get("runninghub_prompt_node_id", "6"))
    field_name = cfg.get("runninghub_prompt_field", "text")
    base_url = cfg.get("runninghub_base_url", "https://www.runninghub.ai")

    headers = {"Content-Type": "application/json"}

    # 1. Create task
    create_payload = {
        "apiKey": api_key,
        "workflowId": workflow_id,
        "nodeInfoList": [
            {"nodeId": node_id, "fieldName": field_name, "fieldValue": prompt}
        ],
    }
    resp = requests.post(f"{base_url}/task/openapi/create", json=create_payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"RunningHub task creation failed: {data.get('msg', data)}")
    task_id = data["data"]["taskId"]

    # 2. Poll for outputs (max 10 minutes)
    max_retries = 120
    for attempt in range(max_retries):
        time.sleep(5)
        poll_resp = requests.post(
            f"{base_url}/task/openapi/outputs",
            json={"apiKey": api_key, "taskId": task_id},
            headers=headers,
            timeout=30,
        )
        poll_resp.raise_for_status()
        poll_data = poll_resp.json()

        if poll_data.get("code") != 0:
            raise RuntimeError(f"RunningHub polling failed: {poll_data.get('msg', poll_data)}")

        task_status = poll_data.get("data", {}).get("taskStatus", "")

        if task_status == "FAILED":
            raise RuntimeError(f"RunningHub task {task_id} failed.")

        if task_status == "SUCCEEDED":
            outputs = poll_data["data"].get("outputs", [])
            if not outputs:
                raise RuntimeError(f"RunningHub task {task_id} succeeded but returned no outputs.")
            file_url = outputs[0].get("fileUrl")
            if not file_url:
                raise RuntimeError(f"RunningHub output missing fileUrl: {outputs[0]}")
            img_resp = requests.get(file_url, timeout=60)
            img_resp.raise_for_status()
            out_path.write_bytes(img_resp.content)
            return

    raise TimeoutError(f"RunningHub task {task_id} did not complete within 10 minutes.")
