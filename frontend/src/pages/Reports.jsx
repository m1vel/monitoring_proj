import { useState, useEffect, useRef } from 'react';
import { Card, DatePicker, Select, Button, Table, Row, Col, Space, Typography, message } from 'antd';
import { SearchOutlined, DownloadOutlined } from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from '../api/client';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import dayjs from 'dayjs';

const { Option } = Select;
const { Title } = Typography;

const Reports = () => {
  const [month, setMonth] = useState(dayjs());
  const [employeeId, setEmployeeId] = useState(undefined);
  const [kpiData, setKpiData] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [employees, setEmployees] = useState([]);
  const reportRef = useRef(null);

  useEffect(() => {
    // Загружаем список сотрудников для фильтра
    api
      .get('/employees/')
      .then((res) => setEmployees(res.data))
      .catch(console.error);
  }, []);

  const fetchReport = async () => {
    setLoading(true);
    try {
      // 1. Данные для таблицы: используем employee_month_matrix и фильтруем
      const matrixRes = await api.get('/queries/employee_month_matrix');
      const allData = matrixRes.data;

      // Фильтрация по выбранному месяцу и сотруднику
      const selectedMonth = month.format('YYYY-MM');
      const filtered = allData.filter((item) => {
        const itemMonth = dayjs(item.period).format('YYYY-MM');
        const matchMonth = itemMonth === selectedMonth;
        const matchEmployee = employeeId ? item.employee_id === employeeId : true;
        return matchMonth && matchEmployee;
      });

      // Преобразуем в удобный для таблицы вид
      const tableData = filtered.map((item) => ({
        full_name: item.full_name,
        productivity_score: item.score,
        employee_id: item.employee_id,
      }));
      setKpiData(tableData);

      // 2. График динамики по отделам (скользящее среднее)
      const chartRes = await api.get('/queries/moving_avg_tasks');
      setChartData(chartRes.data);
    } catch (error) {
      message.error('Ошибка загрузки отчёта');
    } finally {
      setLoading(false);
    }
  };

  const exportPDF = () => {
    const input = document.getElementById('report-container');
    if (!input) return;
    html2canvas(input, { scale: 2 }).then((canvas) => {
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
      pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
      pdf.save('productivity_report.pdf');
    });
  };

  const columns = [
    { title: 'Сотрудник', dataIndex: 'full_name', key: 'name' },
    { title: 'Балл продуктивности', dataIndex: 'productivity_score', key: 'score' },
  ];

  return (
    <div>
      <Title level={2}>Отчёты</Title>
      <div id="report-container" ref={reportRef}>
        <Card style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]} align="middle">
            <Col>
              <DatePicker picker="month" value={month} onChange={setMonth} format="YYYY-MM" />
            </Col>
            <Col>
              <Select
                placeholder="Все сотрудники"
                allowClear
                style={{ width: 250 }}
                value={employeeId}
                onChange={setEmployeeId}
              >
                {employees.map((emp) => (
                  <Option key={emp.id} value={emp.id}>
                    {emp.full_name}
                  </Option>
                ))}
              </Select>
            </Col>
            <Col>
              <Button type="primary" icon={<SearchOutlined />} onClick={fetchReport} loading={loading}>
                Сформировать
              </Button>
            </Col>
            <Col>
              <Button icon={<DownloadOutlined />} onClick={exportPDF}>
                Экспорт PDF
              </Button>
            </Col>
          </Row>
        </Card>

        <Card title="Показатели продуктивности">
          <Table dataSource={kpiData} columns={columns} rowKey="employee_id" pagination={false} />
        </Card>

        {chartData.length > 0 && (
          <Card title="Динамика среднего количества задач по отделам" style={{ marginTop: 16 }}>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="moving_avg_3m" stroke="#8884d8" name="Скользящее среднее" />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        )}
      </div>
    </div>
  );
};

export default Reports;