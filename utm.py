"""
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import re
import math
from qgis.core import QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
try:
    from .util import epsg4326, tr
except ImportError:
    from util import epsg4326, tr

# Geographic coordinate bounds constants
MIN_LONGITUDE = -180
MAX_LONGITUDE = 180
MIN_LATITUDE = -90
MAX_LATITUDE = 90

class UtmException(Exception):
    pass

def utmParse(utm_str):
    utm = utm_str.strip().upper()
    
    # Handle UTM with elevation: "33N 315428 5741324 1234" or "33 N 315428 5741324 1234m"
    m = re.match(r'(\d+)\s*([NS])\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)', utm)
    if m:
        zone = int(m.group(1))
        if zone < 1 or zone > 60:
            raise UtmException(tr('Invalid UTM Coordinate'))
        hemisphere = m.group(2)
        if hemisphere != 'N' and hemisphere != 'S':
            raise UtmException(tr('Invalid UTM Coordinate'))
        easting = float(m.group(3))
        northing = float(m.group(4))
        # Ignore elevation (m.group(5))
        return(zone, hemisphere, easting, northing)
    
    # Standard UTM without elevation: "33 N 315428 5741324"
    m = re.match(r'(\d+)\s*([NS])\s+(\d+\.?\d*)\s+(\d+\.?\d*)', utm)
    if m:
        zone = int(m.group(1))
        if zone < 1 or zone > 60:
            raise UtmException(tr('Invalid UTM Coordinate'))
        hemisphere = m.group(2)
        if hemisphere != 'N' and hemisphere != 'S':
            raise UtmException(tr('Invalid UTM Coordinate'))
        easting = float(m.group(3))
        northing = float(m.group(4))
        return(zone, hemisphere, easting, northing)
    
    # Handle alternative formats with elevation: "315428mE 5741324mN 33N 1234m" 
    m = re.match(
        r'(?P<easting>\d+\.?\d*)\s*M?\s*E\s*,?\s*'
        r'(?P<northing>\d+\.?\d*)\s*M?\s*N\s*,?\s*'
        r'(?P<zone>\d+)\s*(?P<hemisphere>[NS])'
        r'(?:\s*,?\s*(?P<elevation>\d+\.?\d*)\s*M?)?',
        utm
    )
    if m:
        zone = int(m.group('zone'))
        if zone < 1 or zone > 60:
            raise UtmException(tr('Invalid UTM Coordinate'))
        hemisphere = m.group('hemisphere')
        if hemisphere != 'N' and hemisphere != 'S':
            raise UtmException(tr('Invalid UTM Coordinate'))
        easting = float(m.group('easting'))
        northing = float(m.group('northing'))
        # Ignore elevation (m.group('elevation'))
        return(zone, hemisphere, easting, northing)
            
    # Standard alternative format without elevation
    m = re.match(r'(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*,\s*(\d+)\s*([NS])', utm)
    if m is None:
        m = re.match(r'(\d+\.?\d*)\s*M\s*E\s*,\s*(\d+\.?\d*)\s*M\s*N\s*,\s*(\d+)\s*([NS])', utm)
        if m is None:
            m = re.match(r'(\d+\.?\d*)\s*M\s*E\s*,\s*(\d+\.?\d*)\s*M\s*N\s*,\s*(\d+)\s*,\s*([NS])', utm)
    if m:
        zone = int(m.group(3))
        if zone < 1 or zone > 60:
            raise UtmException(tr('Invalid UTM Coordinate'))
        hemisphere = m.group(4)
        if hemisphere != 'N' and hemisphere != 'S':
            raise UtmException(tr('Invalid UTM Coordinate'))
        easting = float(m.group(1))
        northing = float(m.group(2))
        return(zone, hemisphere, easting, northing)
    
    raise UtmException('Invalid UTM Coordinate')

def utm2Point(utm, crs=epsg4326):
    zone, hemisphere, easting, northing = utmParse(utm)
    utmcrs = QgsCoordinateReferenceSystem(utmGetEpsg(hemisphere, zone))
    
    # Validate that the UTM CRS is valid
    if not utmcrs.isValid():
        raise UtmException(f'Cannot create UTM coordinate reference system for zone {zone}, hemisphere {hemisphere}')
    
    pt = QgsPointXY(easting, northing)
    utmtrans = QgsCoordinateTransform(utmcrs, crs, QgsProject.instance())
    
    # Check if transform is valid
    if not utmtrans.isValid():
        raise UtmException('Cannot create coordinate transformation')
    
    transformed_pt = utmtrans.transform(pt)
    
    # Validate that the transformed coordinates are within geographic bounds
    if not (MIN_LONGITUDE <= transformed_pt.x() <= MAX_LONGITUDE) or not (MIN_LATITUDE <= transformed_pt.y() <= MAX_LATITUDE):
        raise UtmException(f'UTM coordinate transformation failed - result outside geographic bounds: {transformed_pt.x()}, {transformed_pt.y()}')
    
    return transformed_pt

def isUtm(utm):
    try:
        z, h, e, n = utmParse(utm)
    except Exception:
        return(False)

    return(True)

def latLon2UtmZone(lat, lon):
    if lon < -180 or lon > 360:
        raise UtmException(tr('Invalid longitude'))
    if lat > 84.5 or lat < -80.5:
        raise UtmException(tr('Invalid latitude'))
    if lon < 180:
        zone = int(31 + (lon / 6.0))
    else:
        zone = int((lon / 6) - 29)

    if zone > 60:
        zone = 1
    # Handle UTM special cases
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32

    if 72.0 <= lat < 84.0:
        if 0.0 <= lon < 9.0:
            zone = 31
        elif 9.0 <= lon < 21.0:
            zone = 33
        elif 21.0 <= lon < 33.0:
            zone = 35
        elif 33.0 <= lon < 42.0:
            zone = 37

    if lat < 0:
        hemisphere = 'S'
    else:
        hemisphere = 'N'
    return(zone, hemisphere)

def latLon2UtmParameters(lat, lon):
    zone, hemisphere = latLon2UtmZone(lat, lon)
    epsg = utmGetEpsg(hemisphere, zone)
    utmcrs = QgsCoordinateReferenceSystem(epsg)
    utmtrans = QgsCoordinateTransform(epsg4326, utmcrs, QgsProject.instance())
    pt = QgsPointXY(lon, lat)
    utmpt = utmtrans.transform(pt)
    return(zone, hemisphere, utmpt.x(), utmpt.y())

def latLon2Utm(lat, lon, precision, format=0):
    try:
        zone, hemisphere, utmx, utmy = latLon2UtmParameters(lat, lon)
        if format == 0:
            msg = '{}{} {:.{prec}f} {:.{prec}f}'.format(zone, hemisphere, utmx, utmy, prec=precision)
        elif format == 1:
            msg = '{:.{prec}f},{:.{prec}f},{}{}'.format(utmx, utmy, zone, hemisphere, prec=precision)
        elif format == 2:
            msg = '{:.{prec}f}mE,{:.{prec}f}mN,{}{}'.format(utmx, utmy, zone, hemisphere, prec=precision)
        else:
            msg = '{:.{prec}f}mE,{:.{prec}f}mN,{},{}'.format(utmx, utmy, zone, hemisphere, prec=precision)
    except Exception:
        msg = ''
    return(msg)

def utmGetEpsg(hemisphere, zone):
    if hemisphere == 'N':
        code = 32600 + zone
    else:
        code = 32700 + zone
    return('EPSG:{}'.format(code))
