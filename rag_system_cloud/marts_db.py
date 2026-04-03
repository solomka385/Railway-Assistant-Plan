# marts_db.py
"""Модуль для работы с витринами данных (equipment_mart, staff_mart, station_responsibles)"""
import logging
from typing import List, Dict, Optional
from math import radians, sin, cos, sqrt, asin

from db import get_pg_connection, return_pg_connection

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Вычисляет расстояние между двумя точками на Земле в километрах."""
    # Преобразуем градусы в радианы
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Формула гаверсинуса
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Радиус Земли в километрах
    r = 6371
    return c * r


def find_nearest_stations(lat: float, lon: float, limit: int = 5) -> List[Dict]:
    """
    Находит ближайшие станции к заданным координатам.
    
    Args:
        lat: Широта
        lon: Долгота
        limit: Максимальное количество станций для возврата
        
    Returns:
        Список словарей с информацией о станциях
    """
    conn = None
    try:
        conn = get_pg_connection()
        if not conn:
            logger.error("Не удалось получить соединение с базой данных")
            return []
        
        cur = conn.cursor()
        
        try:
            # Получаем все станции
            cur.execute("""
                SELECT id, name, latitude, longitude
                FROM rag_app.stations
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            """)
            
            stations = []
            for row in cur.fetchall():
                station_id, name, station_lat, station_lon = row
                distance = haversine_distance(lat, lon, station_lat, station_lon)
                stations.append({
                    'id': station_id,
                    'name': name,
                    'latitude': station_lat,
                    'longitude': station_lon,
                    'distance': distance
                })
            
            # Сортируем по расстоянию и берем limit ближайших
            stations.sort(key=lambda x: x['distance'])
            return stations[:limit]
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса станций: {e}")
            raise
        finally:
            cur.close()
        
    except Exception as e:
        logger.error(f"Ошибка при поиске станций: {e}")
        raise
    finally:
        if conn:
            return_pg_connection(conn)


def get_equipment_by_stations(station_names: List[str], subdivision_codes: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
    """
    Получает данные о технике для указанных станций и подразделений.
    
    Args:
        station_names: Список названий станций
        subdivision_codes: Опциональный список кодов подразделений для фильтрации
        
    Returns:
        Словарь {название_станции: [список техники]}
    """
    conn = None
    try:
        conn = get_pg_connection()
        if not conn:
            logger.error("Не удалось получить соединение с базой данных")
            return {}
        
        cur = conn.cursor()
        
        try:
            result = {}
            
            for station_name in station_names:
                if subdivision_codes:
                    cur.execute("""
                        SELECT subdivision_code, equipment_name, quantity
                        FROM rag_app.equipment_mart
                        WHERE station_name = %s AND subdivision_code = ANY(%s)
                    """, [station_name, subdivision_codes])
                else:
                    cur.execute("""
                        SELECT subdivision_code, equipment_name, quantity
                        FROM rag_app.equipment_mart
                        WHERE station_name = %s
                    """, [station_name])
                
                equipment_list = []
                for row in cur.fetchall():
                    sub_code, eq_name, qty = row
                    equipment_list.append({
                        'subdivision_code': sub_code,
                        'equipment_name': eq_name,
                        'quantity': qty
                    })
                
                result[station_name] = equipment_list
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса техники: {e}")
            raise
        finally:
            cur.close()
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных о технике: {e}")
        raise
    finally:
        if conn:
            return_pg_connection(conn)


def get_staff_by_stations(station_names: List[str], subdivision_codes: Optional[List[str]] = None, 
                          position_names: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
    """
    Получает данные о сотрудниках для указанных станций, подразделений и должностей.
    
    Args:
        station_names: Список названий станций
        subdivision_codes: Опциональный список кодов подразделений для фильтрации
        position_names: Опциональный список названий должностей для фильтрации
        
    Returns:
        Словарь {название_станции: [список сотрудников]}
    """
    conn = None
    try:
        conn = get_pg_connection()
        if not conn:
            logger.error("Не удалось получить соединение с базой данных")
            return {}
        
        cur = conn.cursor()
        
        try:
            result = {}
            
            for station_name in station_names:
                conditions = []
                params = [station_name]
                
                if subdivision_codes:
                    conditions.append("subdivision_code = ANY(%s)")
                    params.append(subdivision_codes)
                if position_names:
                    conditions.append("position_name = ANY(%s)")
                    params.append(position_names)
                
                if conditions:
                    where_clause = " AND " + " AND ".join(conditions)
                    query = f"""
                        SELECT subdivision_code, position_name, quantity
                        FROM rag_app.staff_mart
                        WHERE station_name = %s{where_clause}
                    """
                    cur.execute(query, params)
                else:
                    cur.execute("""
                        SELECT subdivision_code, position_name, quantity
                        FROM rag_app.staff_mart
                        WHERE station_name = %s
                    """, [station_name])
                
                staff_list = []
                for row in cur.fetchall():
                    sub_code, pos_name, qty = row
                    staff_list.append({
                        'subdivision_code': sub_code,
                        'position_name': pos_name,
                        'quantity': qty
                    })
                
                result[station_name] = staff_list
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса сотрудников: {e}")
            raise
        finally:
            cur.close()
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных о сотрудниках: {e}")
        raise
    finally:
        if conn:
            return_pg_connection(conn)


def get_responsibles_by_stations(station_names: List[str], subdivision_codes: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
    """
    Получает данные об ответственных сотрудниках для указанных станций и подразделений.
    
    Args:
        station_names: Список названий станций
        subdivision_codes: Опциональный список кодов подразделений для фильтрации
        
    Returns:
        Словарь {название_станции: [список ответственных]}
    """
    conn = None
    try:
        conn = get_pg_connection()
        if not conn:
            logger.error("Не удалось получить соединение с базой данных")
            return {}
        
        cur = conn.cursor()
        
        try:
            result = {}
            
            for station_name in station_names:
                # Сначала получаем ID станции
                cur.execute("SELECT id FROM rag_app.stations WHERE name = %s", [station_name])
                
                station_row = cur.fetchone()
                if not station_row:
                    result[station_name] = []
                    continue
                
                station_id = station_row[0]
                
                # Получаем ответственных
                if subdivision_codes:
                    cur.execute("""
                        SELECT s.code as subdivision_code, sr.full_name, sr.phone_number, p.name as position_name
                        FROM rag_app.station_responsibles sr
                        JOIN rag_app.subdivisions s ON sr.subdivision_id = s.id
                        LEFT JOIN rag_app.positions p ON sr.employee_id IN (
                            SELECT id FROM rag_app.employees WHERE position_id = p.id
                        )
                        WHERE sr.station_id = %s AND s.code = ANY(%s)
                    """, [station_id, subdivision_codes])
                else:
                    cur.execute("""
                        SELECT s.code as subdivision_code, sr.full_name, sr.phone_number, p.name as position_name
                        FROM rag_app.station_responsibles sr
                        JOIN rag_app.subdivisions s ON sr.subdivision_id = s.id
                        LEFT JOIN rag_app.positions p ON sr.employee_id IN (
                            SELECT id FROM rag_app.employees WHERE position_id = p.id
                        )
                        WHERE sr.station_id = %s
                    """, [station_id])
                
                responsibles_list = []
                for row in cur.fetchall():
                    sub_code, full_name, phone, pos_name = row
                    responsibles_list.append({
                        'subdivision_code': sub_code,
                        'full_name': full_name,
                        'phone_number': phone,
                        'position_name': pos_name
                    })
                
                result[station_name] = responsibles_list
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса ответственных: {e}")
            raise
        finally:
            cur.close()
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных об ответственных: {e}")
        raise
    finally:
        if conn:
            return_pg_connection(conn)


def get_marts_data_by_geo(geo_tags: List[Dict], subdivisions: Optional[List[str]] = None,
                          positions: Optional[List[str]] = None, equipment: Optional[List[str]] = None) -> Dict:
    """
    Получает данные из витрин на основе геометок и фильтров.
    
    Args:
        geo_tags: Список геометок [{'lat': ..., 'lon': ...}]
        subdivisions: Опциональный список кодов подразделений
        positions: Опциональный список должностей
        equipment: Опциональный список техники
        
    Returns:
        Словарь с данными из витрин
    """
    result = {
        'stations': [],
        'equipment': {},
        'staff': {},
        'responsibles': {}
    }
    
    # Находим ближайшие станции для каждой геометки
    all_station_names = set()
    
    for geo_tag in geo_tags:
        lat = geo_tag.get('lat')
        lon = geo_tag.get('lon')
        
        if lat is None or lon is None:
            continue
        
        nearest_stations = find_nearest_stations(lat, lon, limit=3)
        
        for station in nearest_stations:
            if station['name'] not in all_station_names:
                all_station_names.add(station['name'])
                result['stations'].append(station)
    
    station_names_list = list(all_station_names)
    
    if not station_names_list:
        return result
    
    # Получаем данные о технике
    result['equipment'] = get_equipment_by_stations(station_names_list, subdivisions)
    
    # Фильтрация по технике, если указан фильтр
    if equipment:
        filtered_equipment = {}
        for station_name, eq_list in result['equipment'].items():
            filtered_list = [eq for eq in eq_list if eq['equipment_name'] in equipment]
            filtered_equipment[station_name] = filtered_list
        result['equipment'] = filtered_equipment
    
    # Получаем данные о сотрудниках
    result['staff'] = get_staff_by_stations(station_names_list, subdivisions, positions)
    
    # Получаем данные об ответственных
    result['responsibles'] = get_responsibles_by_stations(station_names_list, subdivisions)
    
    return result
