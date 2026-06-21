from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

import httpx

from app.models import CalendarResponse

logger = logging.getLogger(__name__)

CALCULATION_METHODS = {
    "MWL": 3,       # Muslim World League
    "ISNA": 2,      # Islamic Society of North America
    "Egypt": 5,     # Egyptian General Authority
    "Makkah": 4,    # Umm al-Qura, Mecca
    "Karachi": 1,   # University of Islamic Sciences, Karachi
    "Tehran": 7,    # Institute of Geophysics, Tehran
    "Jafari": 0,    # Shia Ithna Ashari
}

UPCOMING_EVENTS = [
    {"month": 1, "day": 1, "name": "Islamic New Year (1st Muharram)"},
    {"month": 1, "day": 10, "name": "Day of Ashura"},
    {"month": 3, "day": 12, "name": "Mawlid al-Nabi ﷺ (Birth of the Prophet)"},
    {"month": 7, "day": 27, "name": "Laylat al-Mi'raj (Night Journey)"},
    {"month": 8, "day": 15, "name": "Laylat al-Bara'a (Night of Forgiveness)"},
    {"month": 9, "day": 1, "name": "Start of Ramadan (approximate)"},
    {"month": 9, "day": 27, "name": "Laylat al-Qadr (Night of Power, approximate)"},
    {"month": 10, "day": 1, "name": "Eid al-Fitr"},
    {"month": 12, "day": 9, "name": "Day of Arafah"},
    {"month": 12, "day": 10, "name": "Eid al-Adha"},
]


async def get_calendar(
    lat: float,
    lon: float,
    aladhan_base: str,
    madhab: str = "general",
    tz: str = "UTC",
) -> CalendarResponse:
    method_key = "Jafari" if madhab == "jafari" else "MWL"
    method_num = CALCULATION_METHODS[method_key]
    school_num = 1 if madhab == "hanafi" else 0
    today = datetime.now(timezone.utc)
    date_str = today.strftime("%d-%m-%Y")

    prayer_times: dict[str, str] = {}
    hijri_date = ""
    hijri_month = ""
    hijri_year = 0

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Prayer times
            pt_resp = await client.get(
                f"{aladhan_base}/timings/{date_str}",
                params={"latitude": lat, "longitude": lon, "method": method_num, "school": school_num},
            )
            pt_resp.raise_for_status()
            pt_data = pt_resp.json()
            timings = pt_data.get("data", {}).get("timings", {})
            prayer_times = {
                k: v for k, v in timings.items()
                if k in ("Fajr", "Dhuhr", "Asr", "Maghrib", "Isha", "Sunrise", "Sunset", "Midnight")
            }

            # Hijri date
            hijri_info = pt_data.get("data", {}).get("date", {}).get("hijri", {})
            hijri_date = f"{hijri_info.get('day', '')} {hijri_info.get('month', {}).get('en', '')} {hijri_info.get('year', '')}"
            hijri_month = hijri_info.get("month", {}).get("en", "")
            hijri_year = int(hijri_info.get("year", 0) or 0)

            # Qibla direction
            qibla_resp = await client.get(f"{aladhan_base}/qibla/{lat}/{lon}")
            qibla_resp.raise_for_status()
            qibla_direction = float(qibla_resp.json().get("data", {}).get("direction", 0))

    except Exception as exc:
        logger.warning("AlAdhan API failed: %s", exc)
        qibla_direction = 0.0

    # Upcoming Islamic events with approximate dates
    upcoming = []
    try:
        current_h_month = int(hijri_info.get("month", {}).get("number", 1))
        current_h_day = int(hijri_info.get("day", 1))
        
        for event in UPCOMING_EVENTS:
            e_month = event["month"]
            e_day = event["day"]
            
            # Calculate days difference (approx 29.5 days per month)
            month_diff = e_month - current_h_month
            if month_diff < 0 or (month_diff == 0 and e_day < current_h_day):
                month_diff += 12 # Next year
                
            days_diff = int((month_diff * 29.5) + (e_day - current_h_day))
            
            # Approximate Gregorian date
            target_date = today + timedelta(days=days_diff)
            gregorian_str = target_date.strftime("%d %b %Y")
            
            # Formatted Hijri date string (e.g. 1st Muharram)
            month_names = ["", "Muharram", "Safar", "Rabi al-Awwal", "Rabi al-Thani", "Jumada al-Awwal", "Jumada al-Thani", "Rajab", "Sha'ban", "Ramadan", "Shawwal", "Dhu al-Qi'dah", "Dhu al-Hijjah"]
            hijri_str = f"{e_day} {month_names[e_month]}"
            
            # Extract just the name without the parenthesis if present
            base_name = event["name"].split(" (")[0]
            upcoming.append({
                "name": base_name, 
                "hijri": hijri_str,
                "gregorian": gregorian_str,
                "_sort_key": days_diff
            })
            
        # Sort by upcoming first and take top 4
        upcoming.sort(key=lambda x: x["_sort_key"])
        upcoming = [{"name": u["name"], "hijri": u["hijri"], "gregorian": u["gregorian"]} for u in upcoming[:4]]
    except Exception as e:
        logger.error(f"Error calculating dates: {e}")
        # Fallback
        for event in UPCOMING_EVENTS[:4]:
            upcoming.append({"name": event["name"], "hijri": "", "gregorian": ""})

    return CalendarResponse(
        hijri_date=hijri_date or "Unavailable",
        hijri_month=hijri_month,
        hijri_year=hijri_year,
        gregorian_date=today.strftime("%d %B %Y"),
        prayer_times=prayer_times,
        qibla_direction=qibla_direction,
        upcoming_events=upcoming,
        timezone=tz,
        calculation_method=method_key,
    )
