from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class XRayLabelDefinition:
    code: str
    display_name: str
    anatomical_region: str
    default_threshold: float
    description: str
    clinical_language: str
    safety_language: str
    evidence_category: str = "CHEST_XRAY_FINDING"


XRAY_LABEL_TAXONOMY: Dict[str, XRayLabelDefinition] = {
    "CARDIOMEGALY": XRayLabelDefinition(
        code="CARDIOMEGALY",
        display_name="Cardiomegaly Pattern",
        anatomical_region="MEDIASTINUM / CARDIAC",
        default_threshold=0.50,
        description="Enlargement of the cardiac silhouette where cardiothoracic ratio exceeds 0.50.",
        clinical_language="Model output indicates a radiographic pattern associated with enlarged cardiac silhouette.",
        safety_language="Finding requires clinician/radiologist verification. Automated model output is not a confirmed clinical diagnosis.",
    ),
    "PLEURAL_EFFUSION": XRayLabelDefinition(
        code="PLEURAL_EFFUSION",
        display_name="Pleural Effusion Pattern",
        anatomical_region="PLEURAL_SPACE",
        default_threshold=0.45,
        description="Blunting of the costophrenic angle or meniscus sign indicative of pleural fluid accumulation.",
        clinical_language="Model detected a radiographic pattern associated with fluid attenuation in the pleural space.",
        safety_language="Finding requires clinician/radiologist verification. Automated model output is not a confirmed clinical diagnosis.",
    ),
    "ATELECTASIS": XRayLabelDefinition(
        code="ATELECTASIS",
        display_name="Atelectasis Pattern",
        anatomical_region="LUNG_PARENCHYMA",
        default_threshold=0.50,
        description="Linear or discoid opacification consistent with partial lung parenchymal volume loss.",
        clinical_language="Model output shows a pattern consistent with subsegmental or lobar volume loss / atelectasis.",
        safety_language="Finding requires clinician/radiologist verification. Automated model output is not a confirmed clinical diagnosis.",
    ),
    "CONSOLIDATION": XRayLabelDefinition(
        code="CONSOLIDATION",
        display_name="Consolidation Pattern",
        anatomical_region="ALVEOLAR_SPACE",
        default_threshold=0.50,
        description="Dense opacification with obscuration of pulmonary vessels and possible air bronchograms.",
        clinical_language="Model output indicates elevated probability of alveolar space opacification / consolidation.",
        safety_language="Finding requires clinician/radiologist verification. Automated model output is not a confirmed clinical diagnosis.",
    ),
    "EDEMA": XRayLabelDefinition(
        code="EDEMA",
        display_name="Pulmonary Edema Pattern",
        anatomical_region="INTERSTITIUM / ALVEOLI",
        default_threshold=0.45,
        description="Bilateral perihilar haze, cephalization of pulmonary vasculature, or Kerley lines.",
        clinical_language="Model detected features associated with interstitial or alveolar pulmonary congestion.",
        safety_language="Finding requires clinician/radiologist verification. Automated model output is not a confirmed clinical diagnosis.",
    ),
    "PNEUMOTHORAX": XRayLabelDefinition(
        code="PNEUMOTHORAX",
        display_name="Pneumothorax Pattern",
        anatomical_region="PLEURAL_SPACE",
        default_threshold=0.40,
        description="Visible visceral pleural line with absent peripheral lung vascular markings.",
        clinical_language="Model detected a pattern associated with pleural gas / pneumothorax.",
        safety_language="Requires immediate radiologist/physician verification. Automated model output is not a confirmed clinical diagnosis.",
    ),
    "INFILTRATION": XRayLabelDefinition(
        code="INFILTRATION",
        display_name="Infiltration Pattern",
        anatomical_region="LUNG_PARENCHYMA",
        default_threshold=0.50,
        description="Ill-defined ill-demarcated parenchymal density.",
        clinical_language="Model output shows patchy or diffuse parenchymal infiltration.",
        safety_language="Finding requires clinician/radiologist verification. Automated model output is not a confirmed clinical diagnosis.",
    ),
    "MASS": XRayLabelDefinition(
        code="MASS",
        display_name="Pulmonary Mass Pattern (>3cm)",
        anatomical_region="LUNG_PARENCHYMA",
        default_threshold=0.40,
        description="Circumscribed pulmonary density measuring greater than 3 cm in greatest dimension.",
        clinical_language="Model identified a focal density pattern larger than 3 cm.",
        safety_language="Finding requires urgent clinician/radiologist review and dedicated diagnostic workup.",
    ),
    "NODULE": XRayLabelDefinition(
        code="NODULE",
        display_name="Pulmonary Nodule Pattern (<=3cm)",
        anatomical_region="LUNG_PARENCHYMA",
        default_threshold=0.45,
        description="Well-defined discrete round or oval pulmonary opacity measuring 3 cm or less.",
        clinical_language="Model detected a focal nodular opacity.",
        safety_language="Finding requires clinician/radiologist verification and comparison with prior imaging.",
    ),
    "PNEUMONIA": XRayLabelDefinition(
        code="PNEUMONIA",
        display_name="Pneumonia Pattern",
        anatomical_region="LUNG_PARENCHYMA",
        default_threshold=0.50,
        description="Infectious parenchymal infiltrate / bronchoalveolar opacification.",
        clinical_language="Model output indicates a pattern associated with infective pulmonary infiltrate.",
        safety_language="Finding requires clinician/radiologist verification. Automated model output is not a confirmed clinical diagnosis.",
    ),
    "FIBROSIS": XRayLabelDefinition(
        code="FIBROSIS",
        display_name="Fibrosis Pattern",
        anatomical_region="INTERSTITIUM",
        default_threshold=0.50,
        description="Reticular opacities, traction bronchiectasis, or volume loss.",
        clinical_language="Model detected reticular interstitial patterns consistent with fibrotic changes.",
        safety_language="Finding requires clinician/radiologist verification. Automated model output is not a confirmed clinical diagnosis.",
    ),
    "PLEURAL_THICKENING": XRayLabelDefinition(
        code="PLEURAL_THICKENING",
        display_name="Pleural Thickening Pattern",
        anatomical_region="PLEURA",
        default_threshold=0.50,
        description="Non-dependent thickening of the visceral or parietal pleura.",
        clinical_language="Model detected radiographic features associated with pleural apical or lateral thickening.",
        safety_language="Finding requires clinician/radiologist verification. Automated model output is not a confirmed clinical diagnosis.",
    ),
}


def get_all_xray_labels() -> List[XRayLabelDefinition]:
    return list(XRAY_LABEL_TAXONOMY.values())


def get_xray_label(code: str) -> Optional[XRayLabelDefinition]:
    return XRAY_LABEL_TAXONOMY.get(code.upper())
