import { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Select, DatePicker, message, Space } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import api from '../api/client';
import dayjs from 'dayjs';

const Employees = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState(null);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await api.get('/employees/');
      setData(response.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAdd = () => {
    setEditingEmployee(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingEmployee(record);
    form.setFieldsValue({
      ...record,
      hire_date: record.hire_date ? dayjs(record.hire_date) : null,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/employees/${id}`);
      message.success('Сотрудник удалён');
      fetchData();
    } catch (error) {
      message.error('Не удалось удалить');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        hire_date: values.hire_date.format('YYYY-MM-DD'),
      };

      if (editingEmployee) {
        await api.put(`/employees/${editingEmployee.id}`, payload);
        message.success('Сотрудник обновлён');
      } else {
        await api.post('/employees/', payload);
        message.success('Сотрудник создан');
      }
      setModalVisible(false);
      fetchData();
    } catch (error) {
      console.error(error);
    }
  };

  const columns = [
    { title: 'ФИО', dataIndex: 'full_name', key: 'name' },
    { title: 'Должность', dataIndex: 'position', key: 'position' },
    { title: 'Отдел', dataIndex: 'department', key: 'department' },
    { title: 'Email', dataIndex: 'email', key: 'email' },
    { title: 'Роль', dataIndex: 'role', key: 'role' },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button icon={<EditOutlined />} size="small" onClick={() => handleEdit(record)} />
          <Button icon={<DeleteOutlined />} size="small" danger onClick={() => handleDelete(record.id)} />
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>Сотрудники</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>Добавить</Button>
      </div>

      <Table dataSource={data} columns={columns} loading={loading} rowKey="id" />

      <Modal
        title={editingEmployee ? 'Редактировать сотрудника' : 'Новый сотрудник'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="login" label="Логин" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          {!editingEmployee && (
            <Form.Item name="password" label="Пароль" rules={[{ required: true }]}>
              <Input.Password />
            </Form.Item>
          )}
          <Form.Item name="full_name" label="ФИО" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="position" label="Должность" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="department" label="Отдел">
            <Input />
          </Form.Item>
          <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="hire_date" label="Дата приёма" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="role" label="Роль" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="admin">Admin</Select.Option>
              <Select.Option value="manager">Manager</Select.Option>
              <Select.Option value="employee">Employee</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="manager_id" label="Руководитель (ID)">
            <Input type="number" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Employees;