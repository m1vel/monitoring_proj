import { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, InputNumber, Input, Select, message, Space } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import api from '../api/client';

const { Option } = Select;

const Reviews = () => {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [form] = Form.useForm();

  const fetchReviews = async () => {
    setLoading(true);
    try {
      const response = await api.get('/reviews/');
      setReviews(response.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTasks = async () => {
    try {
      const res = await api.get('/tasks/');
      setTasks(res.data.filter(t => t.status === 'done'));
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    fetchReviews();
    fetchTasks();
  }, []);

  const handleAdd = () => {
    form.resetFields();
    setModalVisible(true);
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/reviews/${id}`);
      message.success('Оценка удалена');
      fetchReviews();
    } catch (error) {
      message.error('Ошибка удаления');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await api.post('/reviews/', values);
      message.success('Оценка создана');
      setModalVisible(false);
      fetchReviews();
    } catch (error) {
      console.error(error);
    }
  };

  const getCurrentUserRole = () => {
    const token = localStorage.getItem('access_token');
    if (!token) return '';
    try { return JSON.parse(atob(token.split('.')[1])).role; } catch (e) { return ''; }
  };

  const columns = [
    { title: 'Задача', dataIndex: 'task_id', key: 'task',
      render: (tid) => tasks.find(t => t.id === tid)?.title || tid },
    { title: 'Оценка', dataIndex: 'rating', key: 'rating' },
    { title: 'Комментарий', dataIndex: 'comment', key: 'comment' },
    { title: 'Кто оценил', dataIndex: 'reviewer_id', key: 'reviewer' },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => {
        const role = getCurrentUserRole();
        if (role === 'admin') {
          return (
            <Button icon={<DeleteOutlined />} size="small" danger onClick={() => handleDelete(record.id)} />
          );
        }
        return null;
      },
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>Оценки задач</h2>
        {(getCurrentUserRole() === 'admin' || getCurrentUserRole() === 'manager') && (
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>Добавить</Button>
        )}
      </div>

      <Table dataSource={reviews} columns={columns} loading={loading} rowKey="id" />

      <Modal
        title="Новая оценка"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="task_id" label="Задача" rules={[{ required: true }]}>
            <Select placeholder="Выберите выполненную задачу">
              {tasks.map(t => (
                <Option key={t.id} value={t.id}>{t.title}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="rating" label="Оценка (1-5)" rules={[{ required: true, type: 'number', min: 1, max: 5 }]}>
            <InputNumber min={1} max={5} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="comment" label="Комментарий">
            <Input.TextArea rows={2} />
          </Form.Item>
          {/* reviewer_id определится на бэкенде автоматически? Нет, в схеме требуется. Нужно передать текущего пользователя? У нас в API create_review требует reviewer_id, но можно на бэкенде автоматически подставлять текущего. Предположим, что мы отправляем текущего пользователя. Получим его id из токена. */}
          <Form.Item name="reviewer_id" hidden initialValue={0}>
            <InputNumber />
          </Form.Item>
        </Form>
        {/* Перед отправкой проставим reviewer_id вручную */}
        {modalVisible && (() => {
          const token = localStorage.getItem('access_token');
          if (token) {
            const userId = JSON.parse(atob(token.split('.')[1])).user_id;
            form.setFieldsValue({ reviewer_id: userId });
          }
        })()}
      </Modal>
    </div>
  );
};

export default Reviews;