"""Forward Transverse Mercator projection, EPSG:5186 (Korea 2000 Central Belt).

Plaintext preprocessing, run by both sides before anything is encrypted, so the
circuit needs no latitude dependent constant. Standard series expansion, no
projection dependency. Agreement with pyproj is under one millimetre over the
Korean peninsula.
"""

import numpy as np

A = 6378137.0                      # GRS80 semi-major axis, metres
F = 1.0 / 298.257222101            # GRS80 flattening
LAT0 = np.radians(38.0)            # latitude of origin
LON0 = np.radians(127.0)           # central meridian
K0 = 1.0                           # scale factor
FALSE_E = 200000.0                 # false easting, metres
FALSE_N = 600000.0                 # false northing, metres

E2 = F * (2.0 - F)                 # first eccentricity squared
EP2 = E2 / (1.0 - E2)              # second eccentricity squared


def _meridian_arc(lat):
    """Distance along the meridian from the equator, metres."""
    return A * (
        (1 - E2 / 4 - 3 * E2 ** 2 / 64 - 5 * E2 ** 3 / 256) * lat
        - (3 * E2 / 8 + 3 * E2 ** 2 / 32 + 45 * E2 ** 3 / 1024) * np.sin(2 * lat)
        + (15 * E2 ** 2 / 256 + 45 * E2 ** 3 / 1024) * np.sin(4 * lat)
        - (35 * E2 ** 3 / 3072) * np.sin(6 * lat)
    )


M0 = _meridian_arc(LAT0)


def to_tm(lat_deg, lon_deg):
    """Degrees to EPSG:5186 easting and northing in metres. Scalars or arrays."""
    lat = np.radians(np.asarray(lat_deg, dtype=np.float64))
    lon = np.radians(np.asarray(lon_deg, dtype=np.float64))

    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)
    tan_lat = np.tan(lat)

    N = A / np.sqrt(1 - E2 * sin_lat ** 2)
    T = tan_lat ** 2
    C = EP2 * cos_lat ** 2
    Aa = (lon - LON0) * cos_lat
    M = _meridian_arc(lat)

    x = K0 * N * (
        Aa
        + (1 - T + C) * Aa ** 3 / 6
        + (5 - 18 * T + T ** 2 + 72 * C - 58 * EP2) * Aa ** 5 / 120
    ) + FALSE_E

    y = K0 * (
        M - M0
        + N * tan_lat * (
            Aa ** 2 / 2
            + (5 - T + 9 * C + 4 * C ** 2) * Aa ** 4 / 24
            + (61 - 58 * T + T ** 2 + 600 * C - 330 * EP2) * Aa ** 6 / 720
        )
    ) + FALSE_N

    return x, y