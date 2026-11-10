"""Map a customer's district + area to the right delivery zone.

The zone names here must match the DeliveryZone records seeded by the
``seed_delivery_zones`` command. If a zone is renamed in admin, auto-selection
simply falls back to manual choice (the radios stay visible).
"""

ZONE_INSIDE = "Inside Dhaka"
ZONE_SUBAREA = "Dhaka Sub-area"
ZONE_OUTSIDE = "Outside Dhaka"

# Dhaka city thanas -> charged as "Inside Dhaka".
DHAKA_CITY_AREAS = frozenset({
    "Adabor", "Badda", "Banani", "Bangshal", "Cantonment", "Chawkbazar",
    "Dakshinkhan", "Darus Salam", "Demra", "Dhanmondi", "Gendaria", "Gulshan",
    "Hazaribagh", "Jatrabari", "Kafrul", "Kalabagan", "Kamrangirchar",
    "Khilgaon", "Khilkhet", "Kotwali", "Lalbagh", "Mirpur", "Mohammadpur",
    "Motijheel", "Mugda", "New Market", "Pallabi", "Paltan", "Ramna",
    "Rampura", "Sabujbagh", "Shah Ali", "Shahbagh", "Sher-e-Bangla Nagar",
    "Shyampur", "Sutrapur", "Tejgaon", "Turag", "Uttara", "Uttarkhan",
    "Vatara", "Wari",
})

# Districts adjacent to Dhaka -> charged as "Dhaka Sub-area".
SUBAREA_DISTRICTS = frozenset({"Narayanganj", "Gazipur"})


def classify(district, area):
    """Return the delivery zone name for a district/area pair."""
    if district == "Dhaka":
        return ZONE_INSIDE if area in DHAKA_CITY_AREAS else ZONE_SUBAREA
    if district in SUBAREA_DISTRICTS:
        return ZONE_SUBAREA
    return ZONE_OUTSIDE


def js_config():
    """Data the checkout page needs to run the same rule in the browser."""
    return {
        "dhaka_city_areas": sorted(DHAKA_CITY_AREAS),
        "subarea_districts": sorted(SUBAREA_DISTRICTS),
        "zones": {
            "inside": ZONE_INSIDE,
            "subarea": ZONE_SUBAREA,
            "outside": ZONE_OUTSIDE,
        },
    }
