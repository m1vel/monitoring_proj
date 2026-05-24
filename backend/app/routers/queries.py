from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from .. import database, dependencies, models

router = APIRouter(prefix="/api/queries", tags=["queries"])

# Утилита для выполнения сырого SQL и возврата списка словарей
def execute_raw(db: Session, query: str, params=None):
    return db.execute(text(query), params or {}).mappings().all()

# 1. Доля выполненных задач сотрудника в отделе
@router.get("/done_tasks_share")
def done_tasks_share(db: Session = Depends(database.get_db)):
    query = """
    SELECT e.full_name, e.department, COUNT(t.id) AS done_tasks,
           SUM(COUNT(t.id)) OVER (PARTITION BY e.department) AS dept_total,
           ROUND(100.0 * COUNT(t.id) / SUM(COUNT(t.id)) OVER (PARTITION BY e.department), 2) AS pct
    FROM employees e
    JOIN tasks t ON e.id = t.assignee_id AND t.status = 'done'
    GROUP BY e.id, e.department
    ORDER BY e.department, done_tasks DESC
    """
    return execute_raw(db, query)

# 2. Классификация проектов по загруженности
@router.get("/project_load")
def project_load(db: Session = Depends(database.get_db)):
    query = """
    SELECT p.name, COUNT(t.id) AS task_count,
           CASE WHEN COUNT(t.id) < 5 THEN 'Ненагруженный'
                WHEN COUNT(t.id) BETWEEN 5 AND 10 THEN 'Средний'
                ELSE 'Перегруженный' END AS load_category
    FROM projects p LEFT JOIN tasks t ON p.id = t.project_id
    GROUP BY p.id, p.name
    """
    return execute_raw(db, query)

# 3. Сотрудники с рейтингом выше среднего по отделу (скалярный подзапрос + функция)
@router.get("/above_dept_avg_rating")
def above_dept_avg(db: Session = Depends(database.get_db)):
    query = """
    SELECT e.full_name, e.department,
           fn_avg_rating_employee(e.id) AS emp_avg,
           (SELECT AVG(fn_avg_rating_employee(e2.id)) FROM employees e2
            WHERE e2.department = e.department) AS dept_avg
    FROM employees e
    WHERE fn_avg_rating_employee(e.id) >
          (SELECT AVG(fn_avg_rating_employee(e2.id)) FROM employees e2
           WHERE e2.department = e.department)
    """
    return execute_raw(db, query)

# 4. Проекты с критическими незавершёнными задачами (EXISTS)
@router.get("/projects_with_critical_open")
def projects_with_critical_open(db: Session = Depends(database.get_db)):
    query = """
    SELECT p.id, p.name
    FROM projects p
    WHERE EXISTS (
        SELECT 1 FROM tasks t
        WHERE t.project_id = p.id AND t.priority = 'critical' AND t.status != 'done'
    )
    """
    return execute_raw(db, query)

# 5. Сотрудники, участвующие в проектах указанного менеджера (IN)
@router.get("/employees_in_manager_projects")
def employees_in_manager_projects(manager_id: int = Query(...), db: Session = Depends(database.get_db)):
    query = """
    SELECT e.id, e.full_name
    FROM employees e
    WHERE e.id IN (
        SELECT pm.employee_id FROM project_members pm
        JOIN projects p ON pm.project_id = p.id
        WHERE p.manager_id = :mid
    )
    """
    return execute_raw(db, query, {"mid": manager_id})

# 6. Топ-3 сотрудника по продуктивности за последний месяц (CTE + RANK)
@router.get("/top3_kpi")
def top3_kpi(db: Session = Depends(database.get_db)):
    query = """
    WITH current_kpi AS (
        SELECT employee_id, productivity_score,
               RANK() OVER (ORDER BY productivity_score DESC) AS rnk
        FROM kpi_records
        WHERE period = (SELECT MAX(period) FROM kpi_records)
    )
    SELECT e.full_name, ck.productivity_score, ck.rnk
    FROM current_kpi ck
    JOIN employees e ON ck.employee_id = e.id
    WHERE ck.rnk <= 3
    """
    return execute_raw(db, query)

# 7. Динамика продуктивности (сравнение двух месяцев) — параметры month1, month2
@router.get("/productivity_change")
def productivity_change(month1: str = Query(..., description="YYYY-MM-DD первого месяца"),
                        month2: str = Query(..., description="YYYY-MM-DD второго месяца"),
                        db: Session = Depends(database.get_db)):
    query = """
    WITH cur AS (
        SELECT employee_id, productivity_score FROM kpi_records WHERE period = :m1
    ),
    prev AS (
        SELECT employee_id, productivity_score FROM kpi_records WHERE period = :m2
    )
    SELECT e.full_name, prev.productivity_score AS prev_score, cur.productivity_score AS cur_score
    FROM employees e
    JOIN cur ON e.id = cur.employee_id
    JOIN prev ON e.id = prev.employee_id
    WHERE cur.productivity_score < prev.productivity_score
    """
    return execute_raw(db, query, {"m1": month1, "m2": month2})

# 8. Иерархия подчинённых (рекурсивный CTE) через функцию
@router.get("/subordinates")
def get_subordinates(manager_id: int = Query(...), db: Session = Depends(database.get_db)):
    # Вызов табличной функции fn_get_subordinates
    result = db.execute(
        text("SELECT * FROM fn_get_subordinates(:mid)"),
        {"mid": manager_id}
    ).mappings().all()
    return result

# 9. Восходящая иерархия от сотрудника к корню
@router.get("/hierarchy_up")
def hierarchy_up(employee_id: int = Query(...), db: Session = Depends(database.get_db)):
    query = """
    WITH RECURSIVE upwards AS (
        SELECT id, full_name, manager_id FROM employees WHERE id = :eid
        UNION ALL
        SELECT e.id, e.full_name, e.manager_id
        FROM employees e JOIN upwards u ON e.id = u.manager_id
    )
    SELECT * FROM upwards
    """
    return execute_raw(db, query, {"eid": employee_id})

# 10. Перерасход времени по задачам с рангом внутри проекта
@router.get("/overtime_rank")
def overtime_rank(db: Session = Depends(database.get_db)):
    query = """
    SELECT p.name AS project, t.title,
           (t.actual_hours - t.estimated_hours) AS overtime,
           RANK() OVER (PARTITION BY t.project_id ORDER BY (t.actual_hours - t.estimated_hours) DESC) AS overtime_rank
    FROM tasks t
    JOIN projects p ON t.project_id = p.id
    WHERE t.actual_hours IS NOT NULL AND t.estimated_hours IS NOT NULL
      AND t.actual_hours > t.estimated_hours
    """
    return execute_raw(db, query)

# 11. Скользящее среднее числа задач по отделам за 3 месяца
@router.get("/moving_avg_tasks")
def moving_avg_tasks(db: Session = Depends(database.get_db)):
    query = """
    WITH monthly AS (
        SELECT e.department, kr.period, SUM(kr.tasks_completed) AS total_tasks
        FROM kpi_records kr
        JOIN employees e ON kr.employee_id = e.id
        GROUP BY e.department, kr.period
    )
    SELECT department, period, total_tasks,
           AVG(total_tasks) OVER (PARTITION BY department ORDER BY period
                                   ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS moving_avg_3m
    FROM monthly
    ORDER BY department, period
    """
    return execute_raw(db, query)

# 12. Статистика отделов (материализованное представление)
@router.get("/department_stats")
def department_stats(db: Session = Depends(database.get_db)):
    return execute_raw(db, "SELECT * FROM mv_department_stats")

# 13. Детальный отчёт по задачам с оценками
@router.get("/tasks_with_reviews")
def tasks_with_reviews(db: Session = Depends(database.get_db)):
    query = """
    SELECT t.title, e.full_name AS assignee, p.name AS project,
           tr.rating, tr.comment
    FROM tasks t
    JOIN employees e ON t.assignee_id = e.id
    JOIN projects p ON t.project_id = p.id
    LEFT JOIN task_reviews tr ON t.id = tr.task_id
    WHERE t.status = 'done'
    """
    return execute_raw(db, query)

# 14. Сотрудники с >5 просроченными задачами
@router.get("/overdue_more_than_5")
def overdue_more_than_5(db: Session = Depends(database.get_db)):
    query = """
    SELECT e.full_name, COUNT(*) AS overdue_count
    FROM tasks t
    JOIN employees e ON t.assignee_id = e.id
    WHERE t.deadline IS NOT NULL AND t.updated_at::DATE > t.deadline AND t.status = 'done'
    GROUP BY e.id, e.full_name
    HAVING COUNT(*) > 5
    """
    return execute_raw(db, query)

# 15. Топ-3 продуктивности по отделам (использует представление v_employee_kpi_current)
@router.get("/top3_by_department")
def top3_by_department(db: Session = Depends(database.get_db)):
    query = "SELECT * FROM v_employee_kpi_current WHERE productivity_rank <= 3 ORDER BY department"
    return execute_raw(db, query)

# 16. Генерация всех пар сотрудник-месяц 2025 с KPI
@router.get("/employee_month_matrix")
def employee_month_matrix(db: Session = Depends(database.get_db)):
    query = """
    WITH months AS (
        SELECT generate_series('2025-01-01'::DATE, '2025-12-01'::DATE, INTERVAL '1 month') AS period
    )
    SELECT e.full_name, e.id AS employee_id, m.period, COALESCE(kr.productivity_score, 0) AS score
    FROM employees e
    CROSS JOIN months m
    LEFT JOIN kpi_records kr ON e.id = kr.employee_id AND kr.period = m.period
    WHERE e.role = 'employee'
    """
    return execute_raw(db, query)

# 17. Запуск расчёта KPI за месяц (вызов хранимой процедуры)
@router.post("/calculate_kpi")
def calculate_kpi(period: str = Query(..., description="Первое число месяца, YYYY-MM-DD"),
                  db: Session = Depends(database.get_db),
                  current_user: models.Employee = Depends(dependencies.require_role('admin'))):
    db.execute(text("CALL sp_calculate_kpi(:p)"), {"p": period})
    db.commit()
    return {"status": "KPI calculated", "period": period}

# 18. Сравнение средних рейтингов за два квартала
@router.get("/compare_quarter_ratings")
def compare_quarter_ratings(
    q1_start: str = Query(...), q1_end: str = Query(...),
    q2_start: str = Query(...), q2_end: str = Query(...),
    db: Session = Depends(database.get_db)
):
    query = """
    SELECT e.full_name,
           fn_avg_rating_employee(e.id, :q1s, :q1e) AS q1_avg,
           fn_avg_rating_employee(e.id, :q2s, :q2e) AS q2_avg
    FROM employees e
    WHERE e.role = 'employee'
    """
    return execute_raw(db, query, {"q1s": q1_start, "q1e": q1_end, "q2s": q2_start, "q2e": q2_end})

# 19. Сотрудники с рейтингом выше, чем у их менеджера
@router.get("/rating_higher_than_manager")
def rating_higher_than_manager(db: Session = Depends(database.get_db)):
    query = """
    SELECT e.full_name, fn_avg_rating_employee(e.id) AS emp_rating
    FROM employees e
    WHERE fn_avg_rating_employee(e.id) >
          (SELECT AVG(fn_avg_rating_employee(m.id)) FROM employees m WHERE m.id = e.manager_id)
    """
    return execute_raw(db, query)

# 20. Изменение рейтинга (LAG) – падение >0.5
@router.get("/rating_drop")
def rating_drop(db: Session = Depends(database.get_db)):
    query = """
    WITH ratings AS (
        SELECT employee_id, period, avg_quality_rating,
               LAG(avg_quality_rating) OVER (PARTITION BY employee_id ORDER BY period) AS prev_rating
        FROM kpi_records
    )
    SELECT e.full_name, r.period, r.prev_rating, r.avg_quality_rating
    FROM ratings r
    JOIN employees e ON r.employee_id = e.id
    WHERE r.prev_rating IS NOT NULL AND (r.prev_rating - r.avg_quality_rating) > 0.5
    """
    return execute_raw(db, query)

# 21. Обновление материализованного представления (admin)
@router.post("/refresh_materialized_views")
def refresh_mv(db: Session = Depends(database.get_db),
               current_user: models.Employee = Depends(dependencies.require_role('admin'))):
    db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_department_stats"))
    db.commit()
    return {"status": "Materialized view refreshed"}