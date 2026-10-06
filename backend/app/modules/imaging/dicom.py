import io
import struct
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from app.core.logging import logger

# Essential standard DICOM tags (Group, Element)
TAG_STUDY_DATE = (0x0008, 0x0020)
TAG_MODALITY = (0x0008, 0x0060)
TAG_STUDY_INSTANCE_UID = (0x0020, 0x000D)
TAG_SERIES_INSTANCE_UID = (0x0020, 0x000E)
TAG_SOP_INSTANCE_UID = (0x0008, 0x0018)
TAG_BODY_PART = (0x0018, 0x0015)
TAG_VIEW_POSITION = (0x0018, 0x5101)
TAG_ROWS = (0x0028, 0x0010)
TAG_COLUMNS = (0x0028, 0x0011)
TAG_BITS_ALLOCATED = (0x0028, 0x0100)
TAG_PHOTOMETRIC_INTERPRETATION = (0x0028, 0x0004)


def extract_phi_minimized_dicom_metadata(file_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts strictly clinical acquisition parameters from DICOM dataset while
    enforcing privacy boundaries (PHI minimization).
    Does NOT extract patient name, patient address, or identifiable institutional identifiers.
    """
    metadata: Dict[str, Any] = {
        "modality": "XRAY",
        "body_part": "CHEST",
        "view_position": "PA",
        "study_date": None,
        "study_instance_uid": None,
        "series_instance_uid": None,
        "sop_instance_uid": None,
        "rows": 512,
        "columns": 512,
        "bits_allocated": 8,
        "photometric_interpretation": "MONOCHROME2",
    }

    try:
        import pydicom
        ds = pydicom.dcmread(io.BytesIO(file_bytes), stop_before_pixels=True, force=True)
        
        modality_val = getattr(ds, "Modality", "CR")
        metadata["modality"] = "XRAY" if modality_val in ("CR", "DX", "RG", "XR") else modality_val
        metadata["body_part"] = getattr(ds, "BodyPartExamined", "CHEST") or "CHEST"
        metadata["view_position"] = getattr(ds, "ViewPosition", "PA") or "PA"
        
        date_val = getattr(ds, "StudyDate", None)
        if date_val and len(str(date_val)) == 8:
            try:
                metadata["study_date"] = datetime.strptime(str(date_val), "%Y%m%d").isoformat()
            except Exception:
                pass

        metadata["study_instance_uid"] = getattr(ds, "StudyInstanceUID", None)
        metadata["series_instance_uid"] = getattr(ds, "SeriesInstanceUID", None)
        metadata["sop_instance_uid"] = getattr(ds, "SOPInstanceUID", None)
        metadata["rows"] = int(getattr(ds, "Rows", 512) or 512)
        metadata["columns"] = int(getattr(ds, "Columns", 512) or 512)
        metadata["bits_allocated"] = int(getattr(ds, "BitsAllocated", 8) or 8)
        metadata["photometric_interpretation"] = getattr(ds, "PhotometricInterpretation", "MONOCHROME2")
        return metadata
    except ImportError:
        pass
    except Exception as e:
        logger.warning("pydicom header parsing fallback triggered: %s", str(e))

    # Pure Python Lightweight DICOM Header Fallback Reader
    try:
        # Check standard 128 byte preamble + 'DICM'
        if len(file_bytes) >= 132 and file_bytes[128:132] == b"DICM":
            offset = 132
            # Read elements iteratively
            while offset + 8 <= min(len(file_bytes), 4096):
                group, elem = struct.unpack("<HH", file_bytes[offset:offset+4])
                offset += 4
                
                # Check for explicit VR vs implicit VR
                vr_bytes = file_bytes[offset:offset+2]
                try:
                    vr_str = vr_bytes.decode("ascii")
                except Exception:
                    vr_str = ""

                if vr_str in ("UI", "CS", "SH", "LO", "DA", "TM", "US", "SS", "UL", "SL", "DS", "IS", "PN"):
                    offset += 2
                    length = struct.unpack("<H", file_bytes[offset:offset+2])[0]
                    offset += 2
                else:
                    length = struct.unpack("<I", file_bytes[offset:offset+4])[0]
                    offset += 4

                if length > 0 and offset + length <= len(file_bytes):
                    val_bytes = file_bytes[offset:offset+length]
                    offset += length
                    tag = (group, elem)
                    try:
                        val_str = val_bytes.decode("utf-8", errors="ignore").strip("\x00 \t\n\r")
                    except Exception:
                        val_str = ""

                    if tag == TAG_MODALITY and val_str:
                        metadata["modality"] = "XRAY" if val_str in ("CR", "DX", "RG", "XR") else val_str
                    elif tag == TAG_BODY_PART and val_str:
                        metadata["body_part"] = val_str
                    elif tag == TAG_VIEW_POSITION and val_str:
                        metadata["view_position"] = val_str
                    elif tag == TAG_STUDY_INSTANCE_UID and val_str:
                        metadata["study_instance_uid"] = val_str
                    elif tag == TAG_SERIES_INSTANCE_UID and val_str:
                        metadata["series_instance_uid"] = val_str
                    elif tag == TAG_SOP_INSTANCE_UID and val_str:
                        metadata["sop_instance_uid"] = val_str
                    elif tag == TAG_ROWS and len(val_bytes) >= 2:
                        metadata["rows"] = struct.unpack("<H", val_bytes[:2])[0]
                    elif tag == TAG_COLUMNS and len(val_bytes) >= 2:
                        metadata["columns"] = struct.unpack("<H", val_bytes[:2])[0]
                    elif tag == TAG_BITS_ALLOCATED and len(val_bytes) >= 2:
                        metadata["bits_allocated"] = struct.unpack("<H", val_bytes[:2])[0]
                else:
                    break
    except Exception as e:
        logger.debug("Pure Python DICOM fallback reader note: %s", str(e))

    return metadata


def parse_dicom_metadata_and_dimensions(file_bytes: bytes) -> Tuple[int, int, int, str]:
    """
    Extracts dimensions (width, height, bit_depth, color_space) for DICOM validation.
    """
    meta = extract_phi_minimized_dicom_metadata(file_bytes)
    width = meta.get("columns", 512)
    height = meta.get("rows", 512)
    bit_depth = meta.get("bits_allocated", 8)
    color_space = "GRAYSCALE" if "MONOCHROME" in meta.get("photometric_interpretation", "MONOCHROME2") else "RGB"
    return width, height, bit_depth, color_space
