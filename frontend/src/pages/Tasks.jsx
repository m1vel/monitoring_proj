import { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Select, DatePicker, InputNumber, message, Space, Tag } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import api from '../api/client';
import dayjs from 'dayjs';

const { Option } = Select;

const Tasks = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [form] = Form.useForm();
  const [employees, setEmployees] = useState([]);
  const [projects, setProjects] = useState([]);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const response = await api.get('/tasks/');
      setData(response.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const fetchEmployees = async () => {
    try {
      const res = await api.get('/employees/');
      setEmployees(res.data);
    } catch (error) {
      console.error(error);
    }
  };

  const fetchProjects = async () => {
    try {
      const res = await api.get('/projects/');
      setProjects(res.data);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    fetchTasks();
    fetchEmployees();
    fetchProjects();
  }, []);

  const getCurrentUserRole = () => {
    const token = localStorage.getItem('access_token');
    if (!token) return '';
    try {
      return JSON.parse(atob(token.split('.')[1])).role;
    } catch (e) {
      return '';
    }
  };

  const handleAdd = () => {
    setEditingTask(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingTask(record);
    form.setFieldsValue({
      ...record,
      deadline: record.deadline ? dayjs(record.deadline) : null,
      estimated_hours: record.estimated_hours,
      actual_hours: record.actual_hours,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/tasks/${id}`);
      message.success('Задача удалена');
      fetchTasks();
    } catch (error) {
      message.error('Ошибка удаления');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        deadline: values.deadline ? values.deadline.format('YYYY-MM-DD') : null,
      };

      if (editingTask) {
        // employee может обновлять только статус и actual_hours
        if (getCurrentUserRole() === 'employee') {
          const allowed = { status: values.status, actual_hours: values.actual_hours };
          await api.put(`/tasks/${editingTask.id}`, allowed);
        } else {
          await api.put(`/tasks/${editingTask.id}`, payload);
        }
        message.success('Задача обновлена');
      } else {
        await api.post('/tasks/', payload);
        message.success('Задача создана');
      }
      setModalVisible(false);
      fetchTasks();
    } catch (error) {
      console.error(error);
    }
  };

  const columns = [
    { title: 'Заголовок', dataIndex: 'title', key: 'title' },
    { title: 'Проект', dataIndex: 'project_id', key: 'project',
      render: (pid) => projects.find(p => p.id === pid)?.name || pid },
    { title: 'Исполнитель', dataIndex: 'assignee_id', key: 'assignee',
      render: (eid) => employees.find(e => e.id === eid)?.full_name || eid },
    { title: 'Приоритет', dataIndex: 'priority', key: 'priority',
      render: (p) => {
        const color = p === 'critical' ? 'red' : p === 'high' ? 'orange' : p === 'medium' ? 'blue' : 'green';
        return <Tag color={color}>{p}</Tag>;
      } },
    { title: 'Статус', dataIndex: 'status', key: 'status',
      render: (s) => {
        const color = s === 'done' ? 'green' : s === 'in_progress' ? 'blue' : s === 'new' ? 'gray' : 'red';
        return <Tag color={color}>{s}</Tag>;
      } },
    { title: 'Дедлайн', dataIndex: 'deadline', key: 'deadline', render: (text) => text?.slice(0,10) },
    { title: 'Оценка (ч)', dataIndex: 'estimated_hours', key: 'est' },
    { title: 'Факт (ч)', dataIndex: 'actual_hours', key: 'act' },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => {
        const role = getCurrentUserRole();
        const canEdit = role === 'admin' || role === 'manager' || (role === 'employee' && record.assignee_id === JSON.parse(atob(localStorage.getItem('access_token').split('.')[1])).user_id);
        const canDelete = role === 'admin' || role === 'manager';
        return (
          <Space>
            {canEdit && <Button icon={<EditOutlined />} size="small" onClick={() => handleEdit(record)} />}
            {canDelete && <Button icon={<DeleteOutlined />} size="small" danger onClick={() => handleDelete(record.id)} />}
          </Space>
        );
      },
    },
  ];

  // Форма: для сотрудника при редактировании показываем только статус и фактическое время
  const isEmployeeEditing = editingTask && getCurrentUserRole() === 'employee';

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>Задачи</h2>
        {(getCurrentUserRole() === 'admin' || getCurrentUserRole() === 'manager') && (
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>Добавить</Button>
        )}
      </div>

      <Table dataSource={data} columns={columns} loading={loading} rowKey="id" />

      <Modal
        title={editingTask ? 'Редактировать задачу' : 'Новая задача'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="Заголовок" rules={[{ required: true }]}>
            <Input disabled={isEmployeeEditing} />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={3} disabled={isEmployeeEditing} />
          </Form.Item>
          {!editingTask && (
            <>
              <Form.Item name="project_id" label="Проект" rules={[{ required: true }]}>
                <Select placeholder="Выберите проект">
                  {projects.map(p => (
                    <Option key={p.id} value={p.id}>{p.name}</Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item name="assignee_id" label="Исполнитель" rules={[{ required: true }]}>
                <Select placeholder="Выберите сотрудника">
                  {employees.map(e => (
                    <Option key={e.id} value={e.id}>{e.full_name}</Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item name="priority" label="Приоритет" initialValue="medium">
                <Select>
                  <Option value="low">Низкий</Option>
                  <Option value="medium">Средний</Option>
                  <Option value="high">Высокий</Option>
                  <Option value="critical">Критический</Option>
                </Select>
              </Form.Item>
              <Form.Item name="deadline" label="Дедлайн">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="estimated_hours" label="Оценка времени (ч)">
                <InputNumber min={0} step={0.5} style={{ width: '100%' }} />
              </Form.Item>
            </>
          )}
          {editingTask && (
            <>
              <Form.Item name="status" label="Статус">
                <Select>
                  <Option value="new">Новая</Option>
                  <Option value="in_progress">В работе</Option>
                  <Option value="done">Выполнена</Option>
                  <Option value="cancelled">Отменена</Option>
                </Select>
              </Form.Item>
              <Form.Item name="actual_hours" label="Фактическое время (ч)">
                <InputNumber min={0} step={0.5} style={{ width: '100%' }} />
              </Form.Item>
              {!isEmployeeEditing && (
                <>
                  <Form.Item name="priority" label="Приоритет">
                    <Select>
                      <Option value="low">Низкий</Option>
                      <Option value="medium">Средний</Option>
                      <Option value="high">Высокий</Option>
                      <Option value="critical">Критический</Option>
                    </Select>
                  </Form.Item>
                  <Form.Item name="deadline" label="Дедлайн">
                    <DatePicker style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item name="estimated_hours" label="Оценка времени (ч)">
                    <InputNumber min={0} step={0.5} style={{ width: '100%' }} />
                  </Form.Item>
                </>
              )}
            </>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default Tasks;