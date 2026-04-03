from PIL import Image
from PIL.PngImagePlugin import PngInfo
from io import BytesIO
import os
import logging
from typing import Dict, Any, Optional

try:
    import piexif
except ImportError:
    piexif = None

logger = logging.getLogger(__name__)


import tempfile


def update_mp4_metadata(mp4_path: str, metadata_dict: Dict[str, Any]) -> None:
    import subprocess
    import tempfile
    from kaleidescope.config import load_config

    try:
        config = load_config()
        data_dir = config.data_dir
    except Exception:
        data_dir = os.environ.get("DATA_DIR", "./data")

    tmp_dir = os.path.join(data_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    filename = os.path.basename(mp4_path)
    tmp_path = os.path.join(tmp_dir, f"{filename}.tmp.mp4")

    cmd = ["ffmpeg", "-y", "-i", mp4_path, "-movflags", "use_metadata_tags"]
    for key, value in metadata_dict.items():
        str_value = str(value) if not isinstance(value, str) else value
        cmd.extend(["-metadata", f"{key}={str_value}"])
    cmd.extend(["-codec", "copy", tmp_path])

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        os.replace(tmp_path, mp4_path)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error updating MP4 metadata for {mp4_path}: {e.stderr.decode('utf-8')}")
    except Exception as e:
        logger.error(f"Error updating MP4 metadata for {mp4_path}: {e}")


def update_metadata(png_path: str, metadata_dict: Dict[str, Any]) -> None:
    if png_path.lower().endswith(".mp4"):
        return update_mp4_metadata(png_path, metadata_dict)

    try:
        with Image.open(png_path) as img:
            pnginfo = PngInfo()
            if hasattr(img, "text"):
                for key, value in img.text.items():
                    pnginfo.add_text(key, value)

            for key, value in metadata_dict.items():
                str_value = str(value) if not isinstance(value, str) else value
                pnginfo.add_text(key, str_value)

            # Use a temporary file in the DATA_DIR/tmp to make the save atomic
            # This prevents race conditions with watchdog file scanners
            import os
            from kaleidescope.config import load_config

            try:
                config = load_config()
                data_dir = config.data_dir
            except Exception:
                data_dir = os.environ.get("DATA_DIR", "./data")

            tmp_dir = os.path.join(data_dir, "tmp")
            os.makedirs(tmp_dir, exist_ok=True)

            filename = os.path.basename(png_path)
            tmp_path = os.path.join(tmp_dir, f"{filename}.tmp")

            # Save to temporary file
            img.save(tmp_path, format="PNG", pnginfo=pnginfo)

        # Atomic replace
        os.replace(tmp_path, png_path)

    except Exception as e:
        logger.error(f"Error updating metadata for {png_path}: {e}")


def prepare_png_download(source_path: str, doc_data: Dict[str, Any]) -> Optional[bytes]:
    if not os.path.exists(source_path):
        logger.error(f"Image not found: {source_path}")
        return None

    try:
        with Image.open(source_path) as img:
            pnginfo = PngInfo()

            if "text" in doc_data and doc_data["text"]:
                prompt_text = " ".join(
                    item.get("value", item) if isinstance(item, dict) else str(item)
                    for item in doc_data["text"]
                )
                pnginfo.add_text("prompt", prompt_text)

            pnginfo.add_text("negative_prompt", "")

            fields = ["workflow_id", "resolution", "orientation", "source", "id"]
            for field in fields:
                if field in doc_data:
                    pnginfo.add_text(field, str(doc_data[field]))

            if "models" in doc_data and doc_data["models"]:
                clean_models = [model.split("/")[-1] for model in doc_data["models"]]
                pnginfo.add_text("models", ", ".join(clean_models))

            if "schedulers" in doc_data and doc_data["schedulers"]:
                pnginfo.add_text("schedulers", ", ".join(doc_data["schedulers"]))

            if "loras" in doc_data and doc_data["loras"]:
                clean_loras = [lora.split("/")[-1] for lora in doc_data["loras"]]
                pnginfo.add_text("loras", ", ".join(clean_loras))

            if "width" in doc_data:
                pnginfo.add_text("width", str(doc_data["width"]))
            if "height" in doc_data:
                pnginfo.add_text("height", str(doc_data["height"]))

            buffer = BytesIO()
            img.save(buffer, format="PNG", pnginfo=pnginfo)
            buffer.seek(0)
            return buffer.getvalue()
    except Exception as e:
        logger.error(f"Error preparing PNG download: {e}")
        return None


def prepare_jpg_download(source_path: str, doc_data: Dict[str, Any]) -> Optional[bytes]:
    if not os.path.exists(source_path):
        logger.error(f"Image not found: {source_path}")
        return None

    try:
        with Image.open(source_path) as img:
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            comment_parts = []
            if "text" in doc_data and doc_data["text"]:
                prompt_text = " ".join(
                    item.get("value", item) if isinstance(item, dict) else str(item)
                    for item in doc_data["text"]
                )
                comment_parts.append(prompt_text + "\n")

            comment_parts.append("Negative prompt: \n")

            if "width" in doc_data and "height" in doc_data:
                comment_parts.append(f"Size: {doc_data['width']}x{doc_data['height']}, ")

            if "models" in doc_data and doc_data["models"]:
                clean_models = [model.split("/")[-1] for model in doc_data["models"]]
                comment_parts.append(f"Model: {', '.join(clean_models)}, ")

            if "schedulers" in doc_data and doc_data["schedulers"]:
                comment_parts.append(f"Scheduler: {doc_data['schedulers'][0]}, ")

            if "loras" in doc_data and doc_data["loras"]:
                clean_loras = [lora.split("/")[-1] for lora in doc_data["loras"]]
                comment_parts.append(f"LoRA: {', '.join(clean_loras)}, ")

            if "workflow_id" in doc_data:
                comment_parts.append(f"Workflow: {doc_data['workflow_id']}, ")

            if "source" in doc_data:
                comment_parts.append(f"Source: {doc_data['source']}, ")

            comment = "".join(comment_parts)

            exif_bytes = b""
            if piexif:
                exif_dict = {"0th": {}, "Exif": {}, "1st": {}, "thumbnail": None, "GPS": {}}
                exif_dict["Exif"][piexif.ExifTags.UserComment] = comment.encode("utf-8")
                exif_bytes = piexif.dump(exif_dict)
            else:
                logger.warning("piexif not installed, JPG metadata will be missing")

            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=95, exif=exif_bytes)
            buffer.seek(0)
            return buffer.getvalue()
    except Exception as e:
        logger.error(f"Error preparing JPG download: {e}")
        return None
