"""Official download URLs, one entry per docs/spec/01_reference_data.md §1–§5 (confirmed 2026-09-30)."""

# source -> list of URLs fetched automatically. dhs_stem is registered manually (01 §7.2).
DOWNLOADS = {
    "federal_register": [
        "https://www.govinfo.gov/content/pkg/FR-2024-07-23/pdf/2024-16127.pdf",
    ],
    "cip2020": [
        "https://nces.ed.gov/ipeds/cipcode/Files/CIPCode2020.csv",
    ],
    "ipeds_completions": [
        "https://nces.ed.gov/ipeds/complete-data-files/C2024_A.zip",
        "https://nces.ed.gov/ipeds/complete-data-files/C2024_A_Dict.zip",
    ],
    "ipeds_hd": [
        "https://nces.ed.gov/ipeds/complete-data-files/HD2024.zip",
    ],
    "scorecard_fos": [
        "https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Field-of-Study_06102026.zip",
        "https://collegescorecard.ed.gov/files/FieldOfStudyDataDocumentation.pdf",
        "https://collegescorecard.ed.gov/files/CollegeScorecardDataDictionary.xlsx",
    ],
}

MANUAL = {
    "dhs_stem": "https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf",
}

# IPEDS data year label for C2024 (awards 2023-07-01 .. 2024-06-30), final release (01 §3).
IPEDS_DATA_YEAR = "2023-24"
