import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { ConfigProvider, Layout, Menu } from 'antd';
import {
  UserOutlined,
  ProjectOutlined,
  UnorderedListOutlined,
  DashboardOutlined,
  BarChartOutlined,
  LogoutOutlined,
  StarOutlined,
} from '@ant-design/icons';
import ruRU from 'antd/locale/ru_RU';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Employees from './pages/Employees';
import Projects from './pages/Projects';
import Tasks from './pages/Tasks';
import Reviews from './pages/Reviews';
import Reports from './pages/Reports';
import PrivateRoute from './components/PrivateRoute';

const { Header, Sider, Content } = Layout;

const LogoutButton = () => {
  const navigate = useNavigate();
  const handleLogout = () => {
    localStorage.removeItem('access_token');
    navigate('/login');
  };
  return (
    <Menu.Item key="logout" icon={<LogoutOutlined />} onClick={handleLogout}>
      Выйти
    </Menu.Item>
  );
};

const AppLayout = ({ children }) => {
  const navigate = useNavigate();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible>
        <div
          style={{
            height: 32,
            margin: 16,
            color: '#fff',
            textAlign: 'center',
            fontWeight: 'bold',
          }}
        >
          Мониторинг
        </div>
        <Menu
          theme="dark"
          mode="inline"
          defaultSelectedKeys={['/']}
          onClick={({ key }) => navigate(key)}
        >
          <Menu.Item key="/" icon={<DashboardOutlined />}>
            Дашборд
          </Menu.Item>
          <Menu.Item key="/employees" icon={<UserOutlined />}>
            Сотрудники
          </Menu.Item>
          <Menu.Item key="/projects" icon={<ProjectOutlined />}>
            Проекты
          </Menu.Item>
          <Menu.Item key="/tasks" icon={<UnorderedListOutlined />}>
            Задачи
          </Menu.Item>
          <Menu.Item key="/reviews" icon={<StarOutlined />}>
            Оценки
          </Menu.Item>
          <Menu.Item key="/reports" icon={<BarChartOutlined />}>
            Отчёты
          </Menu.Item>
          <LogoutButton />
        </Menu>
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px' }}>
          <h2 style={{ margin: 0 }}>Мониторинг продуктивности IT-отдела</h2>
        </Header>
        <Content
          style={{
            margin: '24px',
            padding: 24,
            background: '#fff',
            borderRadius: 8,
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

const App = () => {
  return (
    <ConfigProvider locale={ruRU}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/*"
            element={
              <PrivateRoute allowedRoles={['admin', 'manager', 'employee']}>
                <AppLayout>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/employees" element={<Employees />} />
                    <Route path="/projects" element={<Projects />} />
                    <Route path="/tasks" element={<Tasks />} />
                    <Route path="/reviews" element={<Reviews />} />
                    <Route path="/reports" element={<Reports />} />
                  </Routes>
                </AppLayout>
              </PrivateRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;