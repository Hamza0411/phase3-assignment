from fastapi import FastAPI, Query, HTTPException
from typing import Optional, Dict, Any
import re

app = FastAPI(title="Academic Audit & Planning Engine - Phase 3")

# Full catalog database for testing
CATALOG_DB: Dict[str, Dict[str, Any]] = {
    "COSC3127": {"credits": 3, "prerequisites": [], "cross_list": []},
    "COSC4426": {"credits": 3, "prerequisites": ["COSC-3127"], "cross_list": []},
    "ITEC3506": {"credits": 3, "prerequisites": [], "cross_list": ["COSC-3506"]},
    "COSC3506": {"credits": 3, "prerequisites": [], "cross_list": ["ITEC-3506"]}
}

# Student database for testing
STUDENTS_DB: Dict[str, Dict[str, Any]] = {
    "770001": {
        "history": [
            {"course_code": "COSC-3127", "status": "COMPLETED", "term": "25F", "credits_earned": 3},
            {"course_code": "COSC-3506", "status": "COMPLETED", "term": "26W", "credits_earned": 3}
        ],
        "plan": [
            {"course_code": "COSC-4426", "term": "26F"},
            {"course_code": "ITEC-3506", "term": "26F"}
        ]
    }
}

def normalize_code(code: str) -> str:
    """Format-insensitive course code comparison: uppercase, remove spaces and hyphens."""
    if not code:
        return ""
    return re.sub(r'[\s\-]', '', code.upper())

def term_to_sort_key(term: str) -> int:
    """
    Converts term (<2-digit-year><season>) to an integer for chronological sorting.
    Season order: W (1) < SP (2) < S (3) < F (4)
    """
    if not term:
        return 0
    match = re.match(r'^(\d{2})([A-Za-z]+)$', term.strip())
    if not match:
        return 0
    year_str, season = match.groups()
    year = int(year_str)
    season_map = {'W': 1, 'SP': 2, 'S': 3, 'F': 4}
    return year * 10 + season_map.get(season.upper(), 0)

def is_term_earlier(term_a: str, term_b: str) -> bool:
    """Returns True if term_a is strictly earlier than term_b chronologically."""
    return term_to_sort_key(term_a) < term_to_sort_key(term_b)

@app.get("/api/v1/students/{student_id}/audit-report")
def get_audit_report(student_id: str, strict: Optional[bool] = Query(False)):
    student = STUDENTS_DB.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    history = student.get("history", [])
    plan = student.get("plan", [])

    completed_courses = {}
    earned_credits_set = set()
    total_earned = 0

    # Process history & avoid double-counting retakes
    for h in history:
        norm_code = normalize_code(h.get("course_code", ""))
        status = h.get("status", "").upper()
        credits = h.get("credits_earned", 0)
        term = h.get("term")

        if status == "COMPLETED":
            completed_courses[norm_code] = term
            if norm_code not in earned_credits_set:
                earned_credits_set.add(norm_code)
                total_earned += credits

    timeline_validation = []
    cross_list_violations = []
    total_planned = 0
    has_issues = False

    # Group planned courses by term
    terms_planned = {}
    for p in plan:
        term = p.get("term", "26F")
        terms_planned.setdefault(term, []).append(p)

    sorted_terms = sorted(terms_planned.keys(), key=term_to_sort_key)

    for term in sorted_terms:
        term_errors = []
        for p in terms_planned[term]:
            code = p.get("course_code", "")
            norm_code = normalize_code(code)
            catalog_entry = CATALOG_DB.get(norm_code, {})
            
            total_planned += catalog_entry.get("credits", 3)

            # 1. Prerequisite check across chronological timeline
            prereqs = catalog_entry.get("prerequisites", [])
            for req in prereqs:
                req_norm = normalize_code(req)
                if req_norm not in completed_courses or not is_term_earlier(completed_courses[req_norm], term):
                    has_issues = True
                    term_errors.append({
                        "course_code": code,
                        "type": "MISSING_PREREQUISITE",
                        "message": f"Missing prerequisite: {req}"
                    })

            # 2. Cross-list check against completed courses
            cross_list = catalog_entry.get("cross_list", [])
            for cl in cross_list:
                cl_norm = normalize_code(cl)
                if cl_norm in completed_courses:
                    has_issues = True
                    cross_list_violations.append({
                        "course_code": code,
                        "type": "CROSS_LIST_CONFLICT",
                        "message": f"Cross-listed with completed course {cl}"
                    })

        if term_errors:
            timeline_validation.append({
                "term": term,
                "errors": term_errors
            })

    total_remaining = max(0, 120 - total_earned - total_planned)

    # Strict mode handling
    if has_issues or cross_list_violations:
        status_val = "failed" if strict else "warning"
    else:
        status_val = "ok"

    return {
        "student_id": student_id,
        "status": status_val,
        "timeline_validation": timeline_validation,
        "cross_list_violations": cross_list_violations,
        "credit_summary": {
            "total_earned": total_earned,
            "total_planned": total_planned,
            "total_remaining_for_graduation": total_remaining
        }
    }
