-- Kiem tra DB TU BAO VE du lieu: moi thao tac sai duoi day PHAI bi database tu choi.
-- Chay SAU `alembic upgrade head` va `python -m app.seed` (dung duoc ca profile minimal):
--   docker compose exec -T db psql -U course_user -d course_reg -v ON_ERROR_STOP=1 < backend/tests/sql/verify_constraints.sql
-- Moi khoi: loi dung loai -> in OK; neu thao tac sai lai duoc chap nhan -> RAISE 'FAIL' lam script dung.
-- Khong de lai thay doi nao (moi thao tac sai deu bi hoan tac).
DO $$
BEGIN
  BEGIN
    UPDATE course_offerings SET enrolled_count = capacity + 1 WHERE id = 1;
    RAISE EXCEPTION 'FAIL: enrolled_count > capacity van duoc ghi';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'OK   ck_offerings_enrolled_range'; END;

  BEGIN
    UPDATE course_offerings SET capacity = 0 WHERE id = 1;
    RAISE EXCEPTION 'FAIL: capacity = 0 van duoc ghi';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'OK   ck_offerings_capacity'; END;

  BEGIN
    INSERT INTO prerequisites(course_id, prereq_course_id, type, group_no) VALUES (1, 1, 'AND', 0);
    RAISE EXCEPTION 'FAIL: tien quyet tu tro vao chinh no van duoc ghi';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'OK   ck_prereq_no_self'; END;

  BEGIN
    INSERT INTO prerequisites(course_id, prereq_course_id, type, group_no) VALUES (1, 2, 'OR', 0);
    RAISE EXCEPTION 'FAIL: OR voi group_no = 0 van duoc ghi';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'OK   ck_prereq_group (OR can group_no >= 1)'; END;

  BEGIN
    INSERT INTO prerequisites(course_id, prereq_course_id, type, group_no) VALUES (1, 2, 'AND', 3);
    RAISE EXCEPTION 'FAIL: AND voi group_no > 0 van duoc ghi';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'OK   ck_prereq_group (AND can group_no = 0)'; END;

  BEGIN
    INSERT INTO enrollments(student_id, offering_id)
      SELECT student_id, offering_id FROM enrollments WHERE status = 'ACTIVE' LIMIT 1;
    RAISE EXCEPTION 'FAIL: dang ky ACTIVE trung van duoc ghi';
  EXCEPTION WHEN unique_violation THEN RAISE NOTICE 'OK   uq_enrollments_active'; END;

  BEGIN
    INSERT INTO students(email, password_hash, full_name, role) VALUES ('khong.mssv@x.vn', 'h', 'n', 'student');
    RAISE EXCEPTION 'FAIL: sinh vien khong co MSSV van duoc ghi';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'OK   ck_students_student_has_mssv'; END;

  BEGIN
    INSERT INTO students(email, password_hash, full_name, role, mssv) VALUES ('gv@x.vn', 'h', 'n', 'teacher', 'X1');
    RAISE EXCEPTION 'FAIL: vai tro ngoai student/admin van duoc ghi';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'OK   ck_students_role (chi 2 vai tro)'; END;

  BEGIN
    DELETE FROM courses WHERE code = 'INT101';
    RAISE EXCEPTION 'FAIL: xoa hoc phan dang la tien quyet/co lop van duoc';
  EXCEPTION WHEN foreign_key_violation THEN RAISE NOTICE 'OK   khoa ngoai chan xoa hoc phan dang duoc tham chieu'; END;

  BEGIN
    UPDATE waitlist SET position = 0 WHERE id = (SELECT min(id) FROM waitlist);
    RAISE EXCEPTION 'FAIL: position = 0 van duoc ghi';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'OK   ck_waitlist_position'; END;

  BEGIN
    UPDATE completed_courses SET grade = 11 WHERE ctid = (SELECT ctid FROM completed_courses LIMIT 1);
    RAISE EXCEPTION 'FAIL: diem 11 van duoc ghi';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'OK   ck_completed_grade'; END;

  RAISE NOTICE '== Tat ca rang buoc hoat dong dung ==';
END $$;
