from datetime import datetime


def format_stations(items: list[dict]) -> str:
    if not items:
        return "no stations found"
    lines = []
    for s in items:
        sid = s.get("id") or s.get("stationId") or "?"
        name = s.get("name") or "?"
        lat = (s.get("location") or {}).get("latitude")
        lon = (s.get("location") or {}).get("longitude")
        loc = f" ({lat:.4f}, {lon:.4f})" if lat and lon else ""
        lines.append(f"{sid}  {name}{loc}")
    return "\n".join(lines)


def format_departures(payload: dict) -> str:
    deps = payload.get("departures") or []
    if not deps:
        return "no departures in the requested window"
    lines = []
    for d in deps:
        when = _hhmm(d.get("when") or d.get("plannedWhen"))
        line = (d.get("line") or {})
        line_name = line.get("name") or "?"
        direction = d.get("direction") or "?"
        delay = d.get("delay")
        delay_str = f" +{delay // 60}m" if delay else ""
        platform = d.get("platform") or d.get("plannedPlatform") or "-"
        cancelled = " CANCELLED" if d.get("cancelled") else ""
        lines.append(f"{when}{delay_str}  {line_name:8}  -> {direction:30}  Gleis {platform}{cancelled}")
    return "\n".join(lines)


def format_journeys(payload: dict) -> str:
    journeys = payload.get("journeys") or []
    if not journeys:
        return "no journeys found"
    blocks = []
    for j in journeys:
        legs = j.get("legs") or []
        if not legs:
            continue
        first = legs[0]
        last = legs[-1]
        dep = _hhmm(first.get("departure") or first.get("plannedDeparture"))
        arr = _hhmm(last.get("arrival") or last.get("plannedArrival"))
        dep_p = first.get("departurePlatform") or "-"
        arr_p = last.get("arrivalPlatform") or "-"
        dur = _duration(first.get("departure") or first.get("plannedDeparture"),
                        last.get("arrival") or last.get("plannedArrival"))
        transfers = max(0, len(legs) - 1)
        lines_used = ", ".join((leg.get("line") or {}).get("name") or "?" for leg in legs)
        blocks.append(
            f"{dep} (Gl. {dep_p})  ->  {arr} (Gl. {arr_p})\n"
            f"  duration: {dur}, transfers: {transfers}\n"
            f"  via: {lines_used}"
        )
    return "\n\n".join(blocks)


def format_trip(payload: dict) -> str:
    trip = payload.get("trip") or payload
    line = (trip.get("line") or {}).get("name") or "?"
    direction = trip.get("direction") or "?"
    stopovers = trip.get("stopovers") or []
    header = f"{line} -> {direction}"
    rows = []
    for st in stopovers:
        stop = (st.get("stop") or {}).get("name") or "?"
        arr = _hhmm(st.get("arrival") or st.get("plannedArrival"))
        dep = _hhmm(st.get("departure") or st.get("plannedDeparture"))
        platform = st.get("departurePlatform") or st.get("arrivalPlatform") or "-"
        cancelled = " CANCELLED" if st.get("cancelled") else ""
        rows.append(f"  {arr or '--:--'} / {dep or '--:--'}  Gl. {platform:4}  {stop}{cancelled}")
    return header + "\n" + "\n".join(rows) if rows else header


def format_nearby(items: list[dict]) -> str:
    return format_stations(items)


def format_station_info(payload: dict) -> str:
    name = payload.get("name") or "?"
    sid = payload.get("id") or "?"
    loc = payload.get("location") or {}
    address = payload.get("address") or {}
    facilities = payload.get("ril100") or payload.get("facilities") or {}

    parts = [f"{name} ({sid})"]
    if address:
        city = address.get("city") or ""
        street = address.get("street") or ""
        zipcode = address.get("zipcode") or ""
        line = ", ".join(p for p in (street, f"{zipcode} {city}".strip()) if p)
        if line:
            parts.append(f"address: {line}")
    if loc.get("latitude") and loc.get("longitude"):
        parts.append(f"location: {loc['latitude']:.4f}, {loc['longitude']:.4f}")
    if isinstance(facilities, dict) and facilities:
        flags = [k for k, v in facilities.items() if v]
        if flags:
            parts.append("facilities: " + ", ".join(sorted(flags)))
    return "\n".join(parts)


def _hhmm(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%H:%M")
    except ValueError:
        return iso[:5]


def _duration(start: str | None, end: str | None) -> str:
    if not (start and end):
        return "?"
    try:
        a = datetime.fromisoformat(start.replace("Z", "+00:00"))
        b = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError:
        return "?"
    mins = int((b - a).total_seconds() // 60)
    h, m = divmod(mins, 60)
    return f"{h}h{m:02d}" if h else f"{m}m"
