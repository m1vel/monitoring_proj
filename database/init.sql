DROP TABLE IF EXISTS kpi_records CASCADE;
DROP TABLE IF EXISTS task_reviews CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS project_members CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
--сотрудники
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    login VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    position VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    email VARCHAR(100) NOT NULL UNIQUE,
    hire_date DATE NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin','manager','employee')),
    manager_id INT REFERENCES employees(id) ON DELETE SET NULL
);
--проекты
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','suspended')),
    manager_id INT REFERENCES employees(id) ON DELETE SET NULL
);
--участники
CREATE TABLE project_members (
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    employee_id INT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, employee_id)
);
-- todo: задачи дописать
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(250) NOT NULL,
    description TEXT,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    assignee_id INT REFERENCES employees(id) ON DELETE CASCADE,
    priority VARCHAR(10) NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high','critical')),
    status VARCHAR(20) NOT NULL DEFAULT 'new' CHECK (status IN ('new','in_progress','done','cancelled')),
    deadline DATE,
    estimated_hours NUMERIC(5,1) CHECK (estimated_hours > 0),
    actual_hours NUMERIC(5,1) CHECK (actual_hours >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
--оценки за задачи
CREATE TABLE task_reviews (
    id SERIAL PRIMARY KEY,
    task_id INT NOT NULL UNIQUE REFERENCES tasks(id) ON DELETE CASCADE,
    reviewer_id INT REFERENCES employees(id) ON DELETE SET NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
--продуктивность
CREATE TABLE kpi_records (
    id SERIAL PRIMARY KEY,
    employee_id INT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    period DATE NOT NULL,
    tasks_completed INT NOT NULL DEFAULT 0 CHECK (tasks_completed >= 0),
    avg_quality_rating NUMERIC(3,2) CHECK (avg_quality_rating BETWEEN 0 AND 5),
    on_time_completion_rate NUMERIC(5,2) CHECK (on_time_completion_rate BETWEEN 0 AND 100),
    productivity_score NUMERIC(6,2) GENERATED ALWAYS AS (
        (tasks_completed * avg_quality_rating) * (on_time_completion_rate / 100.0)
    ) STORED,
    UNIQUE (employee_id, period)
);
--индексы
CREATE INDEX idx_tasks_assignee_status ON tasks(assignee_id, status);
CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_deadline ON tasks(deadline) WHERE deadline IS NOT NULL;
CREATE INDEX idx_kpi_employee_period ON kpi_records(employee_id, period DESC);
CREATE INDEX idx_projects_manager ON projects(manager_id);
CREATE INDEX idx_employees_manager ON employees(manager_id);


--триггер обновления при изм. задачи
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

--получение подчинённых
CREATE OR REPLACE FUNCTION fn_get_subordinates(p_manager_id INT)
RETURNS TABLE (employee_id INT, full_name VARCHAR, level INT)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE sub AS (
        SELECT e.id, e.full_name, 1 AS depth
        FROM employees e
        WHERE e.manager_id = p_manager_id
        UNION ALL
        SELECT e.id, e.full_name, s.depth + 1
        FROM employees e
        JOIN sub s ON e.manager_id = s.employee_id
    )
    SELECT sub.employee_id, sub.full_name, sub.depth FROM sub;
END;
$$;
--оценка сотруника
CREATE OR REPLACE FUNCTION fn_avg_rating_employee(
    p_employee_id INT,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS NUMERIC(3,2)
LANGUAGE plpgsql STABLE
AS $$
DECLARE v_avg NUMERIC(3,2);
BEGIN
    SELECT COALESCE(AVG(tr.rating), 0) INTO v_avg
    FROM tasks t
    JOIN task_reviews tr ON t.id = tr.task_id
    WHERE t.assignee_id = p_employee_id
      AND t.status = 'done'
      AND (p_start_date IS NULL OR t.updated_at::DATE >= p_start_date)
      AND (p_end_date IS NULL OR t.updated_at::DATE <= p_end_date);
    RETURN v_avg;
END;
$$;
--запрет на удалф. сотрудника с задачами
CREATE OR REPLACE FUNCTION prevent_delete_employee_with_open_tasks()
RETURNS TRIGGER AS $$
DECLARE open_task_count INT;
BEGIN
    SELECT COUNT(*) INTO open_task_count
    FROM tasks
    WHERE assignee_id = OLD.id AND status IN ('new','in_progress');
    IF open_task_count > 0 THEN
        RAISE EXCEPTION 'нельзя удалить сотрудника %, у него есть незакрытые задачи', OLD.full_name;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_employee_delete
    BEFORE DELETE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION prevent_delete_employee_with_open_tasks();

CREATE OR REPLACE PROCEDURE sp_calculate_kpi(p_period DATE)
LANGUAGE plpgsql
AS $$
DECLARE
    v_first_day DATE := date_trunc('month', p_period)::DATE;
    v_last_day  DATE := (v_first_day + INTERVAL '1 month' - INTERVAL '1 day')::DATE;
    emp RECORD;
    v_completed INT;
    v_avg_rating NUMERIC(3,2);
    v_on_time_rate NUMERIC(5,2);
BEGIN
    FOR emp IN SELECT id FROM employees WHERE role = 'employee' LOOP
        SELECT COUNT(*) INTO v_completed
        FROM tasks
        WHERE assignee_id = emp.id
          AND status = 'done'
          AND updated_at::DATE BETWEEN v_first_day AND v_last_day;

        SELECT COALESCE(AVG(tr.rating), 0) INTO v_avg_rating
        FROM tasks t
        JOIN task_reviews tr ON t.id = tr.task_id
        WHERE t.assignee_id = emp.id
          AND t.status = 'done'
          AND t.updated_at::DATE BETWEEN v_first_day AND v_last_day;

        SELECT CASE WHEN COUNT(*) > 0
                    THEN ROUND(100.0 * COUNT(*) FILTER (WHERE t.deadline IS NOT NULL AND t.updated_at::DATE <= t.deadline) / COUNT(*), 2)
                    ELSE 0 END
        INTO v_on_time_rate
        FROM tasks t
        WHERE t.assignee_id = emp.id
          AND t.status = 'done'
          AND t.updated_at::DATE BETWEEN v_first_day AND v_last_day;

        INSERT INTO kpi_records (employee_id, period, tasks_completed, avg_quality_rating, on_time_completion_rate)
        VALUES (emp.id, v_first_day, v_completed, v_avg_rating, v_on_time_rate)
        ON CONFLICT (employee_id, period) DO UPDATE SET
            tasks_completed = EXCLUDED.tasks_completed,
            avg_quality_rating = EXCLUDED.avg_quality_rating,
            on_time_completion_rate = EXCLUDED.on_time_completion_rate;
    END LOOP;
    RAISE NOTICE 'Готово: KPI за %', v_first_day;
END;
$$;

CREATE OR REPLACE VIEW v_employee_kpi_current AS
SELECT e.id, e.full_name, e.department,
       kr.period, kr.tasks_completed, kr.avg_quality_rating,
       kr.on_time_completion_rate, kr.productivity_score,
       RANK() OVER (ORDER BY kr.productivity_score DESC) AS productivity_rank
FROM employees e
JOIN kpi_records kr ON e.id = kr.employee_id
WHERE kr.period = (SELECT MAX(period) FROM kpi_records);

CREATE OR REPLACE VIEW v_project_progress AS
SELECT p.id AS project_id, p.name,
       COUNT(t.id) AS total_tasks,
       COUNT(t.id) FILTER (WHERE t.status = 'done') AS completed_tasks,
       COUNT(t.id) FILTER (WHERE t.status IN ('new','in_progress')) AS open_tasks,
       ROUND(100.0 * COUNT(t.id) FILTER (WHERE t.status = 'done') / NULLIF(COUNT(t.id), 0), 1) AS completion_pct
FROM projects p
LEFT JOIN tasks t ON p.id = t.project_id
GROUP BY p.id, p.name;

CREATE MATERIALIZED VIEW mv_department_stats AS
SELECT e.department,
       COUNT(DISTINCT e.id) AS employee_count,
       AVG(kr.productivity_score) AS avg_productivity,
       AVG(kr.avg_quality_rating) AS avg_quality
FROM employees e
JOIN kpi_records kr ON e.id = kr.employee_id
WHERE kr.period = (SELECT MAX(period) FROM kpi_records)
GROUP BY e.department;

CREATE UNIQUE INDEX idx_mv_dept ON mv_department_stats (department);

INSERT INTO employees (login, password_hash, full_name, position, department, email, hire_date, role, manager_id) VALUES
('admin', '$2b$12$LJ3m4ys3Lk0TSwHIAZmHwOmHJqFvx2gCF1f6d7JCjyZ7s6vXfTwKa', 'Симонов Тимур Андреевич', 'Владелец', 'IT', 'tsimonov12@gmail.com', '2026-01-10', 'admin', NULL),
('manager1', '$2b$12$LJ3m4ys3Lk0TSwHIAZmHwOmHJqFvx2gCF1f6d7JCjyZ7s6vXfTwKa', 'Петров Петр Петрович', 'Руководитель отдела разработки', 'Разработка', 'manager1@company.com', '2026-01-11', 'manager', 1),
('manager2', '$2b$12$LJ3m4ys3Lk0TSwHIAZmHwOmHJqFvx2gCF1f6d7JCjyZ7s6vXfTwKa', 'Сидорова Анна', 'Руководитель отдела тестирования', 'Тестирование', 'manager2@company.com', '2026-01-12', 'manager', 1),
('emp1', '$2b$12$LJ3m4ys3Lk0TSwHIAZmHwOmHJqFvx2gCF1f6d7JCjyZ7s6vXfTwKa', 'Кузнецов Алексей', 'Старший разработчик', 'Разработка', 'emp1@company.com', '2026-01-13', 'employee', 2),
('emp2', '$2b$12$LJ3m4ys3Lk0TSwHIAZmHwOmHJqFvx2gCF1f6d7JCjyZ7s6vXfTwKa', 'Смирнова Екатерина', 'Разработчик', 'Разработка', 'emp2@company.com', '2026-01-14', 'employee', 2),
('emp3', '$2b$12$LJ3m4ys3Lk0TSwHIAZmHwOmHJqFvx2gCF1f6d7JCjyZ7s6vXfTwKa', 'Заречный Дмитрий', 'Тестировщик', 'Тестирование', 'emp3@company.com', '2026-01-15', 'employee', 3),
('emp4', '$2b$12$LJ3m4ys3Lk0TSwHIAZmHwOmHJqFvx2gCF1f6d7JCjyZ7s6vXfTwKa', 'Зайцева Ольга', 'Младший разработчик', 'Разработка', 'emp4@company.com', '2026-01-16', 'employee', 2);

INSERT INTO projects (name, description, start_date, end_date, status, manager_id) VALUES
('Разработка CRM', 'Внутренняя система управления клиентами', '2026-01-10', '2026-12-31', 'active', 2),
('Мобильное приложение', 'Кроссплатформенное приложение', '2026-01-11', '2026-12-31', 'active', 2),
('Платформа тестирования', 'Автоматизация тестирования', '2026-01-12', '2026-12-31', 'active', 3);

INSERT INTO project_members (project_id, employee_id) VALUES
(1, 4), (1, 5), (1, 6),
(2, 4), (2, 7),
(3, 6), (3, 5);

INSERT INTO tasks (title, description, project_id, assignee_id, priority, status, deadline, estimated_hours, actual_hours) VALUES
('Спроектировать БД CRM', 'Схема базы', 1, 4, 'high', 'done', '2026-02-01', 40, 38),
('Реализовать API аутентификации', 'JWT', 1, 5, 'critical', 'done', '2026-03-15', 60, 70),
('Тестирование модуля клиентов', 'Функциональное тестирование', 1, 6, 'medium', 'done', '2026-04-01', 20, 18),
('Дизайн мобильного приложения', 'Макеты', 2, 7, 'high', 'done', '2026-03-20', 80, 82),
('Вёрстка экранов', 'React Native', 2, 4, 'medium', 'in_progress', '2026-05-01', 120, NULL),
('Нагрузочное тестирование', 'Проверка производительности', 3, 6, 'high', 'new', '2026-05-15', 40, NULL),
('Написание автотестов', 'Selenium + Python', 3, 5, 'medium', 'new', '2026-06-01', 50, NULL);

INSERT INTO task_reviews (task_id, reviewer_id, rating, comment) VALUES
(1, 2, 5, 'Отлично'),
(2, 2, 4, 'Хорошо, но правки были'),
(3, 3, 5, 'Баг-репорты и логи супер'),
(4, 2, 4, 'Макеты норм, чуть поправили');

CALL sp_calculate_kpi('2026-05-01');