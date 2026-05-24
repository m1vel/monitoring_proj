import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Spin, Typography } from 'antd';
import { UserOutlined, ProjectOutlined, CheckCircleOutlined, TrophyOutlined } from '@ant-design/icons';
import api from '../api/client';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [top3, setTop3] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [tasksRes, kpiRes, projRes] = await Promise.all([
          api.get('/tasks/'),                // все задачи (потом подсчитаем)
          api.get('/queries/top3_kpi'),      // топ-3
          api.get('/projects/'),             // количество проектов
        ]);

        const totalTasks = tasksRes.data.length;
        const completedTasks = tasksRes.data.filter(t => t.status === 'done').length;
        const avgKpi = kpiRes.data.length > 0
          ? (kpiRes.data.reduce((sum, item) => sum + item.productivity_score, 0) / kpiRes.data.length).toFixed(1)
          : 0;

        setStats({
          totalTasks,
          completedTasks,
          totalProjects: projRes.data.length,
          avgKpi,
        });
        setTop3(kpiRes.data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const columns = [
    { title: 'Сотрудник', dataIndex: 'full_name', key: 'name' },
    { title: 'Балл продуктивности', dataIndex: 'productivity_score', key: 'score' },
    { title: 'Рейтинг', dataIndex: 'rnk', key: 'rank' },
  ];

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  return (
    <div>
      <Typography.Title level={2}>Дашборд</Typography.Title>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="Всего задач" value={stats.totalTasks} prefix={<ProjectOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Выполнено задач" value={stats.completedTasks} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Проектов" value={stats.totalProjects} prefix={<ProjectOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Средний KPI" value={stats.avgKpi} prefix={<TrophyOutlined />} />
          </Card>
        </Col>
      </Row>
      <Card title="Топ-3 сотрудника по продуктивности">
        <Table dataSource={top3} columns={columns} rowKey="full_name" pagination={false} />
      </Card>
    </div>
  );
};

export default Dashboard;