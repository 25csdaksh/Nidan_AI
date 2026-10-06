# Medical Imaging DICOM Foundation & Privacy Boundary

## 1. Overview & Architecture

DICOM (Digital Imaging and Communications in Medicine) is the international standard for medical images and related information. Chest X-Ray studies ingested into NIDAN AI may originate as DICOM objects or exported PNG/JPEG files.

When handling DICOM objects, NIDAN AI implements a strict **PHI-Minimized Architecture** to prevent privacy leakage into downstream ML inference pipelines, logs, or external AI providers.

---

## 2. Ingested vs Extracted DICOM Tags

| DICOM Tag | Keyword | Purpose | Extracted & Stored |
| :--- | :--- | :--- | :--- |
| `(0020,000D)` | `StudyInstanceUID` | Unique study linking | Yes (Metadata) |
| `(0020,000E)` | `SeriesInstanceUID` | Series grouping | Yes (Metadata) |
| `(0008,0018)` | `SOPInstanceUID` | Image instance linking | Yes (Metadata) |
| `(0008,0060)` | `Modality` | Imaging modality (`CR`, `DX`, `XR`) | Yes (`XRAY`) |
| `(0018,0015)` | `BodyPartExamined` | Anatomical region verification | Yes (`CHEST`) |
| `(0018,5101)` | `ViewPosition` | Projection angle (`PA`, `AP`, `LATERAL`) | Yes (`view_position`) |
| `(0008,0020)` | `StudyDate` | Longitudinal chronology | Yes (`study_date`) |
| `(0028,0010)` | `Rows` | Image height | Yes |
| `(0028,0011)` | `Columns` | Image width | Yes |
| `(0028,0100)` | `BitsAllocated` | Grayscale bit depth (8/16-bit) | Yes |

---

## 3. Strict PHI Privacy Boundary (Stripped / Redacted)

The following identifying tags are **NEVER** extracted, persisted in metadata JSON, or passed to the ML inference layer:
- `(0010,0010)` `PatientName` — **STRIPPED**
- `(0010,0020)` `PatientID` — **STRIPPED** (Database maps via authenticated patient record)
- `(0010,0030)` `PatientBirthDate` — **STRIPPED**
- `(0010,0040)` `PatientSex` — **STRIPPED**
- `(0010,1000)` `OtherPatientIDs` — **STRIPPED**
- `(0008,0080)` `InstitutionName` — **STRIPPED**
- `(0008,0090)` `ReferringPhysicianName` — **STRIPPED**
- `(0008,1048)` `PhysiciansOfRecord` — **STRIPPED**
- `(0008,1070)` `OperatorsName` — **STRIPPED**

---

## 4. De-identification Flow

```
+--------------------------+
|  Incoming DICOM File     | (Contains Patient PHI & Hospital Metadata)
+--------------------------+
             |
             v
+--------------------------+
|  PHI-Minimization Filter | (Strips 0010 tags, private tags, vendor overlays)
+--------------------------+
             |
             +------------------------------+
             |                              |
             v                              v
+--------------------------+  +-------------------------------+
| Secure Storage Backend   |  | Preprocessing & Vision Model  |
| (Encrypted Blob Storage) |  | (Normalized 8/16-bit Grayscale)|
+--------------------------+  +-------------------------------+
```

---

## 5. Implementation Details

- **Native Parser**: Uses standard `pydicom` with graceful fallback to pure-Python lightweight binary reader to support air-gapped environments without compilation dependencies.
- **Verification**: Pixel arrays are verified for decompression safety before passing to the Image Quality Gate.
