// controllers/martsController.js
const { getPool } = require('../db/pool');
const ExcelJS = require('exceljs');

/**
 * Получает данные из витрин (marts) по координатам пользователя
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 */
exports.getMartsData = async (req, res) => {
    const pool = getPool();
    const client = await pool.connect();
    
    try {
        const { geo_tags, subdivisions, positions, equipment } = req.body;

        if (!geo_tags || geo_tags.length === 0) {
            return res.status(400).json({ error: 'Необходимо указать геометки (geo_tags)' });
        }

        // Получаем координаты из первой геометки
        const location = geo_tags[0];
        const latitude = location.latitude;
        const longitude = location.longitude;

        // 1. Получаем ответственных сотрудников на ближайших станциях (только 1 на станцию, максимум 3 станции)
        const responsibleQuery = `
            SELECT DISTINCT ON (sr.station_name)
                sr.station_name,
                sr.employee_full_name,
                sr.position_name,
                sr.subdivision_code,
                sr.station_lat,
                sr.station_lon,
                sr.phone_number
            FROM rag_app.station_responsibles_view sr
            WHERE sr.station_lat IS NOT NULL
              AND sr.station_lon IS NOT NULL
            ORDER BY sr.station_name, (
                6371 * acos(
                    cos(radians($1)) * cos(radians(sr.station_lat)) *
                    cos(radians(sr.station_lon) - radians($2)) +
                    sin(radians($1)) * sin(radians(sr.station_lat))
                )
            ) ASC
            LIMIT 3
        `;

        const responsibleResult = await client.query(responsibleQuery, [latitude, longitude]);
        
        // 2. Получаем технику на ближайших станциях
        const equipmentQuery = `
            SELECT
                station_name,
                equipment_name,
                quantity,
                subdivision_code,
                station_lat,
                station_lon
            FROM rag_app.equipment_mart
            WHERE station_lat IS NOT NULL
              AND station_lon IS NOT NULL
            ORDER BY (
                6371 * acos(
                    cos(radians($1)) * cos(radians(station_lat)) *
                    cos(radians(station_lon) - radians($2)) +
                    sin(radians($1)) * sin(radians(station_lat))
                )
            ) ASC
            LIMIT 20
        `;

        const equipmentResult = await client.query(equipmentQuery, [latitude, longitude]);
        
        // 3. Получаем сотрудников на ближайших станциях
        const staffQuery = `
            SELECT
                station_name,
                position_name,
                quantity,
                subdivision_code,
                station_lat,
                station_lon
            FROM rag_app.staff_mart
            WHERE station_lat IS NOT NULL
              AND station_lon IS NOT NULL
            ORDER BY (
                6371 * acos(
                    cos(radians($1)) * cos(radians(station_lat)) *
                    cos(radians(station_lon) - radians($2)) +
                    sin(radians($1)) * sin(radians(station_lat))
                )
            ) ASC
            LIMIT 20
        `;

        const staffResult = await client.query(staffQuery, [latitude, longitude]);

        // Группируем данные по станциям
        const equipmentByStation = {};
        const staffByStation = {};
        const responsiblesByStation = {};

        // Группировка техники
        for (const row of equipmentResult.rows) {
            if (!equipmentByStation[row.station_name]) {
                equipmentByStation[row.station_name] = [];
            }
            equipmentByStation[row.station_name].push({
                equipment_name: row.equipment_name,
                quantity: row.quantity
            });
        }

        // Группировка сотрудников
        for (const row of staffResult.rows) {
            if (!staffByStation[row.station_name]) {
                staffByStation[row.station_name] = [];
            }
            staffByStation[row.station_name].push({
                position_name: row.position_name,
                quantity: row.quantity
            });
        }

        // Группировка ответственных (только 1 на станцию)
        for (const row of responsibleResult.rows) {
            if (!responsiblesByStation[row.station_name]) {
                responsiblesByStation[row.station_name] = {
                    full_name: row.employee_full_name,
                    position_name: row.position_name,
                    phone_number: row.phone_number
                };
            }
        }

        res.json({
            equipment: equipmentByStation,
            staff: staffByStation,
            responsibles: responsiblesByStation
        });

    } catch (error) {
        console.error('[getMartsData] Error:', error);
        res.status(500).json({
            error: 'Ошибка при получении данных из витрин',
            message: error.message
        });
    } finally {
        client.release();
    }
};

/**
 * Экспортирует данные по станциям в Excel файл
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 */
exports.exportMartsDataToExcel = async (req, res) => {
    const pool = getPool();
    const client = await pool.connect();
    
    try {
        const { geo_tags, subdivisions, positions, equipment } = req.body;

        if (!geo_tags || geo_tags.length === 0) {
            return res.status(400).json({ error: 'Необходимо указать геометки (geo_tags)' });
        }

        // Получаем координаты из первой геометки
        const location = geo_tags[0];
        const latitude = location.latitude;
        const longitude = location.longitude;

        // 1. Получаем ответственных сотрудников на ближайших станциях
        const responsibleQuery = `
            SELECT DISTINCT ON (sr.station_name)
                sr.station_name,
                sr.employee_full_name,
                sr.position_name,
                sr.subdivision_code,
                sr.station_lat,
                sr.station_lon,
                sr.phone_number
            FROM rag_app.station_responsibles_view sr
            WHERE sr.station_lat IS NOT NULL
              AND sr.station_lon IS NOT NULL
            ORDER BY sr.station_name, (
                6371 * acos(
                    cos(radians($1)) * cos(radians(sr.station_lat)) *
                    cos(radians(sr.station_lon) - radians($2)) +
                    sin(radians($1)) * sin(radians(sr.station_lat))
                )
            ) ASC
            LIMIT 3
        `;

        const responsibleResult = await client.query(responsibleQuery, [latitude, longitude]);
        
        // 2. Получаем технику на ближайших станциях
        const equipmentQuery = `
            SELECT
                station_name,
                equipment_name,
                quantity,
                subdivision_code,
                station_lat,
                station_lon
            FROM rag_app.equipment_mart
            WHERE station_lat IS NOT NULL
              AND station_lon IS NOT NULL
            ORDER BY (
                6371 * acos(
                    cos(radians($1)) * cos(radians(station_lat)) *
                    cos(radians(station_lon) - radians($2)) +
                    sin(radians($1)) * sin(radians(station_lat))
                )
            ) ASC
            LIMIT 20
        `;

        const equipmentResult = await client.query(equipmentQuery, [latitude, longitude]);
        
        // 3. Получаем сотрудников на ближайших станциях
        const staffQuery = `
            SELECT
                station_name,
                position_name,
                quantity,
                subdivision_code,
                station_lat,
                station_lon
            FROM rag_app.staff_mart
            WHERE station_lat IS NOT NULL
              AND station_lon IS NOT NULL
            ORDER BY (
                6371 * acos(
                    cos(radians($1)) * cos(radians(station_lat)) *
                    cos(radians(station_lon) - radians($2)) +
                    sin(radians($1)) * sin(radians(station_lat))
                )
            ) ASC
            LIMIT 20
        `;

        const staffResult = await client.query(staffQuery, [latitude, longitude]);

        // Создаем Excel workbook
        const workbook = new ExcelJS.Workbook();
        workbook.creator = 'Railway Assistant';
        workbook.created = new Date();

        // Лист 1: Ответственные по станциям
        const responsibleSheet = workbook.addWorksheet('Ответственные');
        responsibleSheet.columns = [
            { header: 'Станция', key: 'station', width: 30 },
            { header: 'ФИО', key: 'full_name', width: 40 },
            { header: 'Должность', key: 'position', width: 30 },
            { header: 'Подразделение', key: 'subdivision', width: 20 },
            { header: 'Телефон', key: 'phone', width: 15 },
            { header: 'Широта', key: 'lat', width: 12 },
            { header: 'Долгота', key: 'lon', width: 12 }
        ];
        
        for (const row of responsibleResult.rows) {
            responsibleSheet.addRow({
                station: row.station_name,
                full_name: row.employee_full_name,
                position: row.position_name,
                subdivision: row.subdivision_code,
                phone: row.phone_number,
                lat: row.station_lat,
                lon: row.station_lon
            });
        }

        // Лист 2: Техника по станциям
        const equipmentSheet = workbook.addWorksheet('Техника');
        equipmentSheet.columns = [
            { header: 'Станция', key: 'station', width: 30 },
            { header: 'Наименование техники', key: 'equipment', width: 40 },
            { header: 'Количество', key: 'quantity', width: 12 },
            { header: 'Подразделение', key: 'subdivision', width: 20 },
            { header: 'Широта', key: 'lat', width: 12 },
            { header: 'Долгота', key: 'lon', width: 12 }
        ];
        
        for (const row of equipmentResult.rows) {
            equipmentSheet.addRow({
                station: row.station_name,
                equipment: row.equipment_name,
                quantity: row.quantity,
                subdivision: row.subdivision_code,
                lat: row.station_lat,
                lon: row.station_lon
            });
        }

        // Лист 3: Сотрудники по станциям
        const staffSheet = workbook.addWorksheet('Сотрудники');
        staffSheet.columns = [
            { header: 'Станция', key: 'station', width: 30 },
            { header: 'Должность', key: 'position', width: 30 },
            { header: 'Количество', key: 'quantity', width: 12 },
            { header: 'Подразделение', key: 'subdivision', width: 20 },
            { header: 'Широта', key: 'lat', width: 12 },
            { header: 'Долгота', key: 'lon', width: 12 }
        ];
        
        for (const row of staffResult.rows) {
            staffSheet.addRow({
                station: row.station_name,
                position: row.position_name,
                quantity: row.quantity,
                subdivision: row.subdivision_code,
                lat: row.station_lat,
                lon: row.station_lon
            });
        }

        // Устанавливаем заголовок для всех листов
        const dateStr = new Date().toLocaleDateString('ru-RU');
        responsibleSheet.views = [{ state: 'frozen', ySplit: 1 }];
        equipmentSheet.views = [{ state: 'frozen', ySplit: 1 }];
        staffSheet.views = [{ state: 'frozen', ySplit: 1 }];

        // Генерируем файл
        res.setHeader(
            'Content-Type',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        );
        res.setHeader(
            'Content-Disposition',
            'attachment; filename="stations_data_' + dateStr.replace(/\./g, '-') + '.xlsx"'
        );

        await workbook.xlsx.write(res);
        res.end();

    } catch (error) {
        console.error('[exportMartsDataToExcel] Error:', error);
        res.status(500).json({
            error: 'Ошибка при экспорте данных в Excel',
            message: error.message
        });
    } finally {
        client.release();
    }
};
