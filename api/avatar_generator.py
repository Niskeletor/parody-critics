"""
🎨 Avatar Generator — ComfyUI FLUX integration for character portrait generation.
Calls Omnius ComfyUI API (Tailscale: 100.84.103.61:8188) to generate character avatars.
"""
import asyncio
import httpx
import json
import uuid
from pathlib import Path

try:
    from utils.logger import get_logger
except ImportError:
    import logging
    def get_logger(name): return logging.getLogger(name)

logger = get_logger("avatar_generator")

# ComfyUI basic FLUX txt2img workflow template
# Uses KSampler + CLIPTextEncode + VAEDecode — minimal workflow for FLUX.1-dev
_FLUX_WORKFLOW = {
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["11", 0], "text": "POSITIVE_PROMPT"}
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["11", 0], "text": "NEGATIVE_PROMPT"}
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["13", 0], "vae": ["10", 0]}
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "avatar", "images": ["8", 0]}
    },
    "10": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
    "11": {
        "class_type": "DualCLIPLoader",
        "inputs": {
            "clip_name1": "clip_l.safetensors",
            "clip_name2": "t5xxl_fp16.safetensors",
            "type": "flux"
        }
    },
    "12": {
        "class_type": "UNETLoader",
        "inputs": {"unet_name": "flux1-dev.safetensors", "weight_dtype": "fp8_e4m3fn"}
    },
    "13": {
        "class_type": "KSampler",
        "inputs": {
            "cfg": 1,
            "denoise": 1,
            "latent_image": ["16", 0],
            "model": ["12", 0],
            "negative": ["7", 0],
            "positive": ["6", 0],
            "sampler_name": "euler",
            "scheduler": "simple",
            "seed": 42,
            "steps": 20
        }
    },
    "16": {
        "class_type": "EmptySD3LatentImage",
        "inputs": {"batch_size": 1, "height": 512, "width": 512}
    }
}


class AvatarGenerator:
    def __init__(self, comfyui_url: str, avatar_dir: str, style_prompt: str, negative_prompt: str):
        self.comfyui_url = comfyui_url.rstrip("/")
        self.avatar_dir = Path(avatar_dir)
        self.style_prompt = style_prompt
        self.negative_prompt = negative_prompt

    async def check_comfyui_available(self) -> bool:
        """Ping ComfyUI /system_stats — returns True if reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.comfyui_url}/system_stats")
                return r.status_code == 200
        except Exception:
            return False

    def _build_prompt(self, character_name: str, personality: str) -> str:
        return f"{character_name}, {personality}, {self.style_prompt}"

    async def generate_avatar(self, character_id: str, character_name: str, personality: str) -> Path:
        """
        Generate avatar via ComfyUI FLUX workflow.
        Returns path to saved PNG file.
        Raises RuntimeError on failure.
        """
        positive = self._build_prompt(character_name, personality)
        workflow = json.loads(json.dumps(_FLUX_WORKFLOW))  # deep copy
        workflow["6"]["inputs"]["text"] = positive
        workflow["7"]["inputs"]["text"] = self.negative_prompt
        # Random seed per generation
        workflow["13"]["inputs"]["seed"] = int(uuid.uuid4().int % (2**32))

        client_id = str(uuid.uuid4())
        payload = {"prompt": workflow, "client_id": client_id}

        async with httpx.AsyncClient(timeout=120) as client:
            # Submit prompt
            r = await client.post(f"{self.comfyui_url}/prompt", json=payload)
            if r.status_code != 200:
                raise RuntimeError(f"ComfyUI /prompt failed: {r.status_code} {r.text[:200]}")

            prompt_id = r.json().get("prompt_id")
            if not prompt_id:
                raise RuntimeError(f"ComfyUI returned no prompt_id: {r.text[:200]}")

            logger.info(f"[avatar] prompt_id={prompt_id} character={character_id}")

            # Poll /history until done (max 120s, 2s intervals = 60 attempts)
            for attempt in range(60):
                await asyncio.sleep(2)
                h = await client.get(f"{self.comfyui_url}/history/{prompt_id}")
                data = h.json()
                if prompt_id not in data:
                    continue

                outputs = data[prompt_id].get("outputs", {})
                # Find SaveImage node output (node "9")
                save_node = outputs.get("9", {})
                images = save_node.get("images", [])
                if not images:
                    continue

                img_info = images[0]
                filename = img_info["filename"]
                subfolder = img_info.get("subfolder", "")

                # Download image from ComfyUI /view
                params = {"filename": filename, "type": "output"}
                if subfolder:
                    params["subfolder"] = subfolder
                img_r = await client.get(f"{self.comfyui_url}/view", params=params)
                if img_r.status_code != 200:
                    raise RuntimeError(f"Failed to download image from ComfyUI: {img_r.status_code}")

                # Save to data/avatars/
                self.avatar_dir.mkdir(parents=True, exist_ok=True)
                dest = self.avatar_dir / f"{character_id}.png"
                dest.write_bytes(img_r.content)
                logger.info(f"[avatar] saved {dest} ({len(img_r.content)} bytes)")
                return dest

        raise RuntimeError(f"ComfyUI generation timed out after 120s for {character_id}")
