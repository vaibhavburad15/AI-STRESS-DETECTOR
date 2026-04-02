from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

NMC_SEARCH_URL = (
    "https://www.nmc.org.in/MCIRest/open/getDataFromService?service=searchDoctor"
)

VERIFICATION_SOURCE_AUTO = "nmc_auto"
VERIFICATION_SOURCE_ADMIN = "admin_manual"

# Council labels are taken from NMC's IMR public dropdown.
STATE_MEDICAL_COUNCIL_IDS: dict[str, int] = {
    "Andhra Pradesh Medical Council": 1,
    "Arunachal Pradesh Medical Council": 2,
    "Assam Medical Council": 3,
    "Bihar Medical Council": 4,
    "Chattisgarh Medical Council": 5,
    "Delhi Medical Council": 6,
    "Goa Medical Council": 7,
    "Gujarat Medical Council": 8,
    "Haryana Medical Council": 9,
    "Himachal Pradesh Medical Council": 10,
    "Jammu & Kashmir Medical Council": 11,
    "Jharkhand Medical Council": 12,
    "Karnataka Medical Council": 13,
    "Madhya Pradesh Medical Council": 15,
    "Maharashtra Medical Council": 16,
    "Manipur Medical Council": 26,
    "Orissa Council of Medical Registration": 17,
    "Punjab Medical Council": 18,
    "Rajasthan Medical Council": 19,
    "Sikkim Medical Council": 20,
    "Tamil Nadu Medical Council": 21,
    "Telangana State Medical Council": 43,
    "Tripura State Medical Council": 22,
    "Uttar Pradesh Medical Council": 23,
    "Uttarakhand Medical Council": 24,
    "West Bengal Medical Council": 25,
    "Bareilly Medical Council": 27,
    "Bhopal Medical Council": 28,
    "Bombay Medical Council": 29,
    "Chandigarh Medical Council": 30,
    "Hyderabad Medical Council": 45,
    "Madras Medical Council": 36,
    "Mahakoshal Medical Council": 35,
    "Mysore Medical Council": 37,
    "Nagaland Medical Council": 41,
    "Pondicherry Medical Council": 38,
    "Travancore Cochin Medical Council": 33,
    "Travancore Cochin Medical Council, Trivandrum": 50,
    "Vidharba Medical Council": 40,
    "Mizoram Medical Council": 42,
}


def normalize_registration_number(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def resolve_state_medical_council_id(state_medical_council: str) -> Optional[int]:
    direct = STATE_MEDICAL_COUNCIL_IDS.get(state_medical_council)
    if direct is not None:
        return direct

    normalized_input = state_medical_council.strip().lower()
    for label, smc_id in STATE_MEDICAL_COUNCIL_IDS.items():
        if label.lower() == normalized_input:
            return smc_id
    return None


def get_state_medical_councils() -> list[str]:
    return sorted(STATE_MEDICAL_COUNCIL_IDS.keys())


def _compose_name(record: dict[str, Any]) -> str:
    parts = [
        str(record.get("firstName") or "").strip(),
        str(record.get("middleName") or "").strip(),
        str(record.get("lastName") or "").strip(),
    ]
    return " ".join([part for part in parts if part]).strip()


def build_nmc_profile(details: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not details:
        return {}

    record = details.get("record") or {}
    if not isinstance(record, dict):
        return {}

    return {
        "full_name": _compose_name(record),
        "registration_number": record.get("registrationNo"),
        "registration_date": record.get("regDate"),
        "year_of_info": record.get("yearInfo"),
        "state_medical_council": record.get("smcName"),
        "date_of_birth": record.get("birthDateStr"),
        "father_or_husband_name": record.get("parentName"),
        "qualification": record.get("doctorDegree"),
        "qualification_year": record.get("yearOfPassing"),
        "university": record.get("university"),
        "uprn_no": record.get("uprnNo"),
        "address": record.get("address"),
        "doctor_id": record.get("doctorId"),
    }


def doctor_has_nmc_verification(doctor: Optional[dict[str, Any]]) -> bool:
    if not doctor:
        return False
    return bool(doctor.get("nmc_verified") or doctor.get("nmc_verification"))


def is_doctor_verified(doctor: Optional[dict[str, Any]]) -> bool:
    if not doctor:
        return False

    # Once a verification source exists, the stored flag is authoritative.
    if doctor.get("verification_source") is not None:
        return bool(doctor.get("is_verified", False))

    # Legacy doctors without a source should be treated as verified if they
    # already passed NMC verification.
    return bool(doctor.get("is_verified", False) or doctor_has_nmc_verification(doctor))


def get_verified_doctors_filter() -> dict[str, Any]:
    return {
        "$or": [
            {"is_verified": True},
            {
                "verification_source": None,
                "nmc_verified": True,
            },
            {
                "verification_source": None,
                "nmc_verification": {"$exists": True, "$ne": None},
            },
        ]
    }


def get_active_verified_doctors_filter() -> dict[str, Any]:
    return {
        **get_verified_doctors_filter(),
        "email_verified": True,
    }


def _pick_best_match(
    records: list[dict[str, Any]], registration_number: str, smc_id: int
) -> Optional[dict[str, Any]]:
    normalized_input = normalize_registration_number(registration_number)
    if not normalized_input:
        return None

    exact_by_smc: list[dict[str, Any]] = []
    exact_any: list[dict[str, Any]] = []
    loose: list[dict[str, Any]] = []

    for record in records:
        record_reg = str(record.get("registrationNo") or "")
        normalized_record = normalize_registration_number(record_reg)
        if not normalized_record:
            continue

        same_smc = int(record.get("smcId") or 0) == smc_id
        if normalized_record == normalized_input and same_smc:
            exact_by_smc.append(record)
        elif normalized_record == normalized_input:
            exact_any.append(record)
        elif same_smc and normalized_input in normalized_record:
            loose.append(record)

    if exact_by_smc:
        return exact_by_smc[0]
    if exact_any:
        return exact_any[0]
    if loose:
        return loose[0]
    return None


def verify_doctor_registration(
    registration_number: str, state_medical_council: str
) -> dict[str, Any]:
    smc_id = resolve_state_medical_council_id(state_medical_council)
    if smc_id is None:
        return {
            "verified": False,
            "error": "Invalid state medical council selected.",
            "details": None,
        }

    payload = {
        "registrationNo": registration_number.strip(),
        "smcId": str(smc_id),
    }

    try:
        request = Request(
            NMC_SEARCH_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=12) as response:
            raw = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError):
        return {
            "verified": False,
            "error": "NMC verification service is currently unavailable.",
            "details": None,
        }

    try:
        records = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "verified": False,
            "error": "NMC verification returned an invalid response.",
            "details": None,
        }

    if not isinstance(records, list) or not records:
        return {
            "verified": False,
            "error": "Doctor not found in NMC Indian Medical Register.",
            "details": None,
        }

    selected_record = _pick_best_match(records, registration_number, smc_id)
    if selected_record is None:
        return {
            "verified": False,
            "error": "Doctor not found in NMC Indian Medical Register.",
            "details": None,
        }

    return {
        "verified": True,
        "error": None,
        "details": {
            "verified_at": datetime.utcnow().isoformat(),
            "source": "NMC_IMR",
            "state_medical_council": state_medical_council,
            "smc_id": smc_id,
            "registration_number_input": registration_number,
            "record": selected_record,
        },
    }
