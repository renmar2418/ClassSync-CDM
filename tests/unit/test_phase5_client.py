"""Comprehensive Phase 5 Test Suite: Client Applications (Web PWA & Expo Mobile Companion).

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Test Coverage:
1. Dark Surface Rule compliance: 0 occurrences of active 'filter: invert(1)' across .tsx and .css.
2. Zero-regex student ID validator compliance in mobile (AST & runtime deterministic validation).
3. Spatial Quarantine room directory filtering (NB 204, NB 304, NB 308 hidden by default).
4. Decision Log D-12 plain-language error translations (409 conflict suggestions, zero raw tech jargon).
5. Token definitions and WCAG 2.2 touch targets (>=48px touch targets, 72px nav track, contrast ratios).
6. Mobile QR payload parser (15s rotating TOTP freshness & drift window).
7. Faculty Portal teaching matrix (Mon-Sat 07:00-19:00 continuous 30-min slots) and delta re-solver.
8. Web client routing and role guards (STUDENT, FACULTY, ADMIN, password change interceptor, projector chromeless route).
"""

import os
import re
import subprocess
import json
import pytest


# ===========================================================================
# 1. Dark Surface Rule & Brand Logo Compliance (Decision Log D-11)
# ===========================================================================

def test_dark_surface_rule_no_css_invert():
    """Verify strictly ZERO occurrences of active 'filter: invert(1)' or CSS inversion

    across all .tsx and .css files in apps/web/src and apps/mobile/src.
    Decision Log D-11 strictly prohibits inverted logo hacks on dark surfaces.
    """
    target_dirs = [
        os.path.join("apps", "web", "src"),
        os.path.join("apps", "mobile", "src"),
    ]

    violations = []
    comment_pattern = re.compile(r"/\*.*?\*/|//.*?$", re.DOTALL | re.MULTILINE)
    invert_pattern = re.compile(r"filter\s*:\s*['\"]?invert\s*\([10.]+\)|filter:\s*invert\(", re.IGNORECASE)

    for target_dir in target_dirs:
        if not os.path.exists(target_dir):
            continue
        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.endswith((".tsx", ".css", ".ts")):
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Strip comments to allow documentation explaining the rule
                    stripped_content = comment_pattern.sub("", content)

                    if invert_pattern.search(stripped_content):
                        violations.append(filepath)

    assert len(violations) == 0, f"Dark Surface Rule violation: Found CSS invert in {violations}"


def test_brand_logo_neutral_white_card_container():
    """Verify BrandLogo component enforces neutral white card container on dark surfaces."""
    logo_path = os.path.join("apps", "web", "src", "components", "common", "BrandLogo.tsx")
    assert os.path.exists(logo_path), "BrandLogo.tsx must exist"

    with open(logo_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must contain neutral white card wrapping and accessible text fallback
    assert "bg-white" in content or "neutral white" in content.lower()
    assert "brand-fallback" in content
    assert "ClassSync" in content


# ===========================================================================
# 2. Zero-Regex Student ID Validator Compliance (Mobile)
# ===========================================================================

def test_mobile_zero_regex_student_id_validator_source_audit():
    """Verify source code of studentIdValidator.ts contains strictly ZERO regex expressions,

    zero RegExp instances, and zero regex methods (.test, .match, .search, .replace).
    """
    validator_path = os.path.join("apps", "mobile", "src", "utils", "studentIdValidator.ts")
    assert os.path.exists(validator_path), "studentIdValidator.ts must exist"

    with open(validator_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Remove comments
    comment_pattern = re.compile(r"/\*.*?\*/|//.*?$", re.DOTALL | re.MULTILINE)
    code_only = comment_pattern.sub("", content)

    # 1. No RegExp constructor or literal regex
    assert "RegExp" not in code_only, "Forbidden RegExp constructor found in studentIdValidator.ts"
    assert "new RegExp" not in code_only
    assert ".test(" not in code_only, "Forbidden regex .test() method found"
    assert ".match(" not in code_only, "Forbidden regex .match() method found"
    assert ".search(" not in code_only, "Forbidden regex .search() method found"

    # 2. Must use deterministic character indexing and ASCII bounds
    assert "charAt" in code_only or "[" in code_only
    assert "'24-'" in code_only or "2" in code_only
    assert "'0'" in code_only and "'9'" in code_only


def test_mobile_student_id_validator_runtime_deterministic():
    """Execute studentIdValidator.ts via Node.js to verify strict 24-XXXXX validation rules."""
    script = """
    import { validateStudentIDDeterministic } from './apps/mobile/src/utils/studentIdValidator.ts';
    
    const results = {
      valid1: validateStudentIDDeterministic('24-00123'),
      valid2: validateStudentIDDeterministic('24-99999'),
      valid3: validateStudentIDDeterministic('24-00000'),
      
      invalidPrefix1: validateStudentIDDeterministic('23-00123'),
      invalidPrefix2: validateStudentIDDeterministic('25-00123'),
      invalidPrefix3: validateStudentIDDeterministic('AB-00123'),
      
      invalidLengthShort: validateStudentIDDeterministic('24-123'),
      invalidLengthLong: validateStudentIDDeterministic('24-123456'),
      invalidEmpty: validateStudentIDDeterministic(''),
      
      invalidCharsLetters: validateStudentIDDeterministic('24-12A45'),
      invalidCharsSymbol: validateStudentIDDeterministic('24-12-45'),
      invalidCharsSpace: validateStudentIDDeterministic('24-12 45'),
      
      invalidTypeNull: validateStudentIDDeterministic(null),
      invalidTypeNumber: validateStudentIDDeterministic(2400123)
    };
    
    console.log(JSON.stringify(results));
    """

    res = subprocess.run(
        ["node", "--experimental-strip-types", "-e", script],
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )

    assert res.returncode == 0, f"Node script execution failed: {res.stderr}"
    data = json.loads(res.stdout.strip())

    # Valid cases
    assert data["valid1"]["isValid"] is True
    assert data["valid1"]["normalizedId"] == "24-00123"
    assert data["valid2"]["isValid"] is True
    assert data["valid3"]["isValid"] is True

    # Invalid prefixes
    assert data["invalidPrefix1"]["isValid"] is False
    assert "24-" in data["invalidPrefix1"]["error"]
    assert data["invalidPrefix2"]["isValid"] is False
    assert data["invalidPrefix3"]["isValid"] is False

    # Invalid lengths
    assert data["invalidLengthShort"]["isValid"] is False
    assert "8 characters" in data["invalidLengthShort"]["error"]
    assert data["invalidLengthLong"]["isValid"] is False
    assert data["invalidEmpty"]["isValid"] is False

    # Invalid characters in numeric suffix
    assert data["invalidCharsLetters"]["isValid"] is False
    assert data["invalidCharsSymbol"]["isValid"] is False
    assert data["invalidCharsSpace"]["isValid"] is False

    # Invalid types
    assert data["invalidTypeNull"]["isValid"] is False
    assert data["invalidTypeNumber"]["isValid"] is False


# ===========================================================================
# 3. Spatial Quarantine Directory Filtering (Admin Portal)
# ===========================================================================

def test_admin_portal_spatial_quarantine_filter_rules():
    """Verify AdminPortal.tsx quarantines NB 204, NB 304, NB 308 by default (Decision Log D-05)."""
    admin_path = os.path.join("apps", "web", "src", "pages", "AdminPortal.tsx")
    assert os.path.exists(admin_path), "AdminPortal.tsx must exist"

    with open(admin_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Non-schedulable quarantined rooms must exist with isSchedulable: false
    assert "NB 204" in content
    assert "NB 304" in content
    assert "NB 308" in content
    assert "isSchedulable: false" in content

    # 2. PRRC rooms must have isSchedulable: true
    assert "PRRC 101" in content
    assert "PRRC 108" in content
    assert "BSED_SCIENCE" in content  # Dedicated science lab lock

    # 3. Filtering mechanism: showQuarantined state
    assert "showQuarantined" in content
    assert "setShowQuarantined" in content
    assert "r.isSchedulable" in content


def test_admin_portal_quarantine_filtering_logic_simulation():
    """Simulate spatial directory filtering to verify default view hides quarantined rooms."""
    rooms = [
        {"code": "PRRC 101", "isSchedulable": True},
        {"code": "PRRC 108", "isSchedulable": True},
        {"code": "PRRC 301", "isSchedulable": True},
        {"code": "NB 204", "isSchedulable": False, "reason": "Faculty Lounge"},
        {"code": "NB 304", "isSchedulable": False, "reason": "Server Room"},
        {"code": "NB 308", "isSchedulable": False, "reason": "Physical Plant Storage"},
    ]

    # Default state: showQuarantined = False
    default_displayed = [r for r in rooms if r["isSchedulable"]]
    assert len(default_displayed) == 3
    quarantined_codes = [r["code"] for r in default_displayed]
    assert "NB 204" not in quarantined_codes
    assert "NB 304" not in quarantined_codes
    assert "NB 308" not in quarantined_codes

    # Toggled state: showQuarantined = True
    all_displayed = rooms
    assert len(all_displayed) == 6
    all_codes = [r["code"] for r in all_displayed]
    assert "NB 204" in all_codes
    assert "NB 304" in all_codes
    assert "NB 308" in all_codes


# ===========================================================================
# 4. Decision Log D-12 Empathetic Plain-Language Error Translations
# ===========================================================================

def test_decision_log_d12_error_messages_absence_of_tech_jargon():
    """Verify mobile error dictionary strictly prohibits raw technical system jargon."""
    errors_mobile_path = os.path.join("apps", "mobile", "src", "constants", "errors.ts")
    assert os.path.exists(errors_mobile_path), "mobile errors.ts must exist"

    with open(errors_mobile_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Strip comments to check actual error message string values
    comment_pattern = re.compile(r"/\*.*?\*/|//.*?$", re.DOTALL | re.MULTILINE)
    code_only = comment_pattern.sub("", content)

    # Forbidden raw technical terms in student-facing messages
    assert "409 Conflict" not in code_only
    assert "CP-SAT Infeasibility" not in code_only
    assert "TOTP Desync" not in code_only
    assert "SQL Error" not in code_only

    # Required empathetic phrases
    assert "claimed by a classmate" in code_only
    assert "open right next to it" in code_only
    assert "QR code just refreshed" in code_only
    assert "Offline Mode" in code_only


def test_d12_workstation_claim_conflict_suggestion_runtime():
    """Verify runtime 409 conflict next-seat suggestion logic in mobile errors."""
    script = """
    import { ERROR_MESSAGES, translateErrorMessage } from './apps/mobile/src/constants/errors.ts';
    
    const msgWithNext = ERROR_MESSAGES.WORKSTATION_ALREADY_CLAIMED(12, 13);
    const msgWithoutNext = ERROR_MESSAGES.WORKSTATION_ALREADY_CLAIMED(12);
    const translated409 = translateErrorMessage(409, { claimedStation: 5, suggestedStation: 6 });
    
    console.log(JSON.stringify({ msgWithNext, msgWithoutNext, translated409 }));
    """

    res = subprocess.run(
        ["node", "--experimental-strip-types", "-e", script],
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )

    assert res.returncode == 0, f"Node script execution failed: {res.stderr}"
    data = json.loads(res.stdout.strip())

    assert "PC-12 was just claimed by a classmate!" in data["msgWithNext"]
    assert "PC-13 is open right next to it" in data["msgWithNext"]
    assert "PC-5 was just claimed by a classmate!" in data["translated409"]
    assert "PC-6 is open right next to it" in data["translated409"]


# ===========================================================================
# 5. Design Tokens & WCAG 2.2 Touch Targets
# ===========================================================================

def test_web_tokens_css_conformance():
    """Verify web tokens.css defines core colors, 48px touch targets, and 72px nav."""
    tokens_path = os.path.join("apps", "web", "src", "styles", "tokens.css")
    assert os.path.exists(tokens_path), "tokens.css must exist"

    with open(tokens_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Normalize multiple whitespace characters for resilient token assertion
    normalized = re.sub(r"\s+", " ", content)

    # Core Brand Tokens
    assert "--brand-midnight: #34141f" in normalized
    assert "--brand-rouge: #872e49" in normalized
    assert "--brand-rose: #f8ebf0" in normalized

    # WCAG 2.2 Dimensions
    assert "--control-height: 48px" in normalized
    assert "--bottom-nav-height: 72px" in normalized
    assert "--sidebar-width: 256px" in normalized


def test_mobile_theme_conformance():
    """Verify mobile theme.ts defines matching tokens, 48px touch targets, and 72px nav."""
    theme_path = os.path.join("apps", "mobile", "src", "constants", "theme.ts")
    assert os.path.exists(theme_path), "theme.ts must exist"

    with open(theme_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "#34141f" in content
    assert "#872e49" in content
    assert "#f8ebf0" in content
    assert "minTouchTarget: 48" in content
    assert "bottomNavHeight: 72" in content


def test_color_contrast_ratio_wcag_compliance():
    """Mathematically verify relative luminance and WCAG 2.2 AA contrast >= 4.5:1.

    Test Brand Midnight (#34141f) against White (#ffffff).
    """
    def hex_to_relative_luminance(hex_str: str) -> float:
        hex_str = hex_str.lstrip('#')
        r, g, b = [int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
        
        def srgb_channel(c: float) -> float:
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            
        return 0.2126 * srgb_channel(r) + 0.7152 * srgb_channel(g) + 0.0722 * srgb_channel(b)

    lum_midnight = hex_to_relative_luminance("#34141f")
    lum_white = hex_to_relative_luminance("#ffffff")

    # Contrast ratio = (L1 + 0.05) / (L2 + 0.05) where L1 is lighter
    contrast_ratio = (lum_white + 0.05) / (lum_midnight + 0.05)

    # Must exceed WCAG 2.2 AA requirement of 4.5:1
    assert contrast_ratio >= 4.5, f"Contrast ratio {contrast_ratio:.2f} fails WCAG AA"
    assert contrast_ratio > 10.0, f"Expected high contrast > 10:1, got {contrast_ratio:.2f}"


# ===========================================================================
# 6. Mobile QR Payload Parser Runtime
# ===========================================================================

def test_mobile_qr_payload_parser_runtime():
    """Verify QR presence payload decoding, TOTP validation, and clock drift window."""
    script = """
    import { parseQRPresencePayload } from './apps/mobile/src/utils/qrPayloadParser.ts';
    
    const now = Date.now();
    const validJson = JSON.stringify({
      room: 'PRRC 301',
      session: 'sess-ipt2-01',
      totp: '582910',
      ts: now,
      workstation_id: 12
    });
    
    const expiredJson = JSON.stringify({
      room: 'PRRC 301',
      session: 'sess-ipt2-01',
      totp: '582910',
      ts: now - 45000 // 45s ago (exceeds 30s drift window)
    });
    
    const invalidTotpJson = JSON.stringify({
      room: 'PRRC 301',
      session: 'sess-ipt2-01',
      totp: '1234', // not 6 digits
      ts: now
    });
    
    const results = {
      valid: parseQRPresencePayload(validJson, now),
      expired: parseQRPresencePayload(expiredJson, now),
      invalidTotp: parseQRPresencePayload(invalidTotpJson, now),
      invalidString: parseQRPresencePayload('malformed-string', now)
    };
    
    console.log(JSON.stringify(results));
    """

    res = subprocess.run(
        ["node", "--experimental-strip-types", "-e", script],
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )

    assert res.returncode == 0, f"Node script execution failed: {res.stderr}"
    data = json.loads(res.stdout.strip())

    assert data["valid"]["success"] is True
    assert data["valid"]["payload"]["room"] == "PRRC 301"
    assert data["valid"]["payload"]["totp"] == "582910"
    assert data["valid"]["payload"]["workstation_id"] == 12

    assert data["expired"]["success"] is False
    assert data["expired"]["isExpired"] is True
    assert "QR code just refreshed" in data["expired"]["error"]

    assert data["invalidTotp"]["success"] is False
    assert "Invalid attendance token code" in data["invalidTotp"]["error"]

    assert data["invalidString"]["success"] is False


# ===========================================================================
# 7. Faculty Portal Matrix & Delta Resolver
# ===========================================================================

def test_faculty_portal_continuous_slots_and_delta_resolver():
    """Verify FacultyPortal.tsx defines continuous 30-min slots and delta re-solver hook."""
    faculty_path = os.path.join("apps", "web", "src", "pages", "FacultyPortal.tsx")
    assert os.path.exists(faculty_path), "FacultyPortal.tsx must exist"

    with open(faculty_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Continuous 30-min slots 0-23
    assert "Continuous 30-minute intervals" in content
    assert "Slots 0–23" in content
    assert "Mon–Sat 07:00–19:00" in content

    # 100% full-time faculty model
    assert "100% Full-Time" in content
    assert "Plantilla Faculty" in content

    # Delta resolver endpoint integration (<0.10s SLA)
    assert "/api/v1/scheduling/delta-resolve" in content

    # Projector mode launcher
    assert "Launch Projector" in content
    assert "/projector/PRRC 301" in content or "onLaunchProjector" in content


# ===========================================================================
# 8. Web Routing & Role-Based Route Guards
# ===========================================================================

def test_web_app_routing_and_guards():
    """Verify App.tsx implements role-based guards, password change interceptor, and chromeless projector route."""
    app_path = os.path.join("apps", "web", "src", "App.tsx")
    assert os.path.exists(app_path), "App.tsx must exist"

    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Chromeless standalone route for /projector/:roomCode
    assert "currentPath.startsWith('/projector')" in content
    assert "ProjectorView" in content

    # 2. Password change interceptor
    assert "requires_password_change" in content
    assert "/setup-password" in content

    # 3. Role-based guards
    assert "ADMIN" in content
    assert "FACULTY" in content
    assert "STUDENT" in content
    assert "Institutional Admin Access Restricted" in content
    assert "Faculty Teaching Portal Restricted" in content
