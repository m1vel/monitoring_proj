import { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Select, DatePicker, message, Space, Tag } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import api from '../api/client';
import dayjs from 'dayjs';

const { Option } = Select;

const Projects = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [form] = Form.useForm();
  const [managers, setManagers] = useState([]);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const response = await api.get('/projects/');
      setData(response.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const fetchManagers = async () => {
    try {
      const response = await api.get('/employees/');
      // фильтруем только менеджеров (или админов)
      const mgrs = response.data.filter(emp => emp.role === 'manager' || emp.role === 'admin');
      setManagers(mgrs);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchManagers();
  }, []);

  const handleAdd = () => {
    setEditingProject(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingProject(record);
    form.setFieldsValue({
      ...record,
      start_date: record.start_date ? dayjs(record.start_date) : null,
      end_date: record.end_date ? dayjs(record.end_date) : null,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/projects/${id}`);
      message.success('Проект удалён');
      fetchProjects();
    } catch (error) {
      message.error('Ошибка удаления');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        start_date: values.start_date.format('YYYY-MM-DD'),
        end_date: values.end_date ? values.end_date.format('YYYY-MM-DD') : null,
      };

      if (editingProject) {
        await api.put(`/projects/${editingProject.id}`, payload);
        message.success('Проект обновлён');
      } else {
        await api.post('/projects/', payload);
        message.success('Проект создан');
      }
      setModalVisible(false);
      fetchProjects();
    } catch (error) {
      console.error(error);
    }
  };

  const columns = [
    { title: 'Название', dataIndex: 'name', key: 'name' },
    { title: 'Описание', dataIndex: 'description', key: 'desc', ellipsis: true },
    { title: 'Начало', dataIndex: 'start_date', key: 'start', render: (text) => text?.slice(0,10) },
    { title: 'Окончание', dataIndex: 'end_date', key: 'end', render: (text) => text?.slice(0,10) },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const color = status === 'active' ? 'green' : status === 'completed' ? 'blue' : 'orange';
        return <Tag color={color}>{status}</Tag>;
      },
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => {
        const token = localStorage.getItem('access_token');
        let role = '';
        if (token) {
          try { role = JSON.parse(atob(token.split('.')[1])).role; } catch(e) {}
        }
        const canEdit = role === 'admin' || role === 'manager'; // manager может редактировать свои проекты
        const canDelete = role === 'admin';
        return (
          <Space>
            {canEdit && <Button icon={<EditOutlined />} size="small" onClick={() => handleEdit(record)} />}
            {canDelete && <Button icon={<DeleteOutlined />} size="small" danger onClick={() => handleDelete(record.id)} />}
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>Проекты</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>Добавить</Button>
      </div>

      <Table dataSource={data} columns={columns} loading={loading} rowKey="id" />

      <Modal
        title={editingProject ? 'Редактировать проект' : 'Новый проект'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="start_date" label="Дата начала" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="end_date" label="Дата окончания">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="status" label="Статус" initialValue="active" rules={[{ required: true }]}>
            <Select>
              <Option value="active">Активный</Option>
              <Option value="completed">Завершён</Option>
              <Option value="suspended">Приостановлен</Option>
            </Select>
          </Form.Item>
          <Form.Item name="manager_id" label="Руководитель" rules={[{ required: true }]}>
            <Select placeholder="Выберите руководителя">
              {managers.map(m => (
                <Option key={m.id} value={m.id}>{m.full_name}</Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Projects;