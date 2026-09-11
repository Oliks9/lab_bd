SET SERVEROUTPUT ON
DECLARE
    v_suffix VARCHAR2(32) := LOWER(RAWTOHEX(SYS_GUID()));
    v_admin NUMBER;
    v_user NUMBER;
    v_peer_one NUMBER;
    v_peer_two NUMBER;
    v_topic NUMBER;
    v_quiz NUMBER;
    v_other_quiz NUMBER;
    v_target NUMBER;
    v_unused NUMBER;

    FUNCTION add_attempt(p_user NUMBER, p_score NUMBER, p_status VARCHAR2 DEFAULT 'FINISHED',
                         p_max NUMBER DEFAULT 100, p_quiz NUMBER DEFAULT NULL) RETURN NUMBER IS
        v_id NUMBER;
    BEGIN
        -- Persisted-score fixtures isolate reporting from answer-scoring tests.
        INSERT INTO attempts (user_id, quiz_id, status, max_points, awarded_points, score_percent)
        VALUES (p_user, NVL(p_quiz, v_quiz), p_status, p_max, p_score, p_score)
        RETURNING attempt_id INTO v_id;
        RETURN v_id;
    END;

    PROCEDURE expect(p_code VARCHAR2, p_average NUMBER, p_difference NUMBER,
                     p_attempts NUMBER, p_users NUMBER) IS
        v_result v_attempt_comparison%ROWTYPE;
    BEGIN
        SELECT * INTO v_result FROM v_attempt_comparison WHERE attempt_id = v_target;
        IF v_result.comparison_code <> p_code
           OR NVL(v_result.peer_average_percent, -999) <> NVL(p_average, -999)
           OR NVL(v_result.difference_pp, -999) <> NVL(p_difference, -999)
           OR v_result.peer_attempt_count <> p_attempts
           OR v_result.peer_user_count <> p_users THEN
            RAISE_APPLICATION_ERROR(-20981, 'Comparison mismatch: expected ' || p_code
                || ', got ' || v_result.comparison_code || ', average='
                || v_result.peer_average_percent || ', difference=' || v_result.difference_pp);
        END IF;
    END;
BEGIN
    SAVEPOINT comparison_test;
    SELECT user_id INTO v_admin FROM app_users
     WHERE role_code = 'ADMIN' AND is_active = 1 AND ROWNUM = 1;
    pr_register_user('cmp_u_' || v_suffix, 'Compare123!', 'Comparison user', v_user);
    pr_register_user('cmp_a_' || v_suffix, 'Compare123!', 'Comparison peer A', v_peer_one);
    pr_register_user('cmp_b_' || v_suffix, 'Compare123!', 'Comparison peer B', v_peer_two);
    pkg_admin.create_topic(v_admin, 'Comparison ' || v_suffix, NULL, v_topic);
    pkg_admin.create_quiz(v_admin, v_topic, 'Compared quiz', NULL, 'QUIZ', 10, NULL, 0, 'PUBLIC', v_quiz);
    pkg_admin.create_quiz(v_admin, v_topic, 'Unrelated quiz', NULL, 'QUIZ', 10, NULL, 1, 'PUBLIC', v_other_quiz);

    v_target := add_attempt(v_user, 80);
    expect('NO_PEERS', NULL, NULL, 0, 0);
    v_unused := add_attempt(v_user, 0);
    expect('NO_PEERS', NULL, NULL, 0, 0);

    v_unused := add_attempt(v_peer_one, 0);
    expect('ABOVE', 0, 80, 1, 1);
    UPDATE attempts SET score_percent = 60, awarded_points = 60 WHERE attempt_id = v_unused;
    v_unused := add_attempt(v_peer_two, 40, 'EXPIRED');
    expect('ABOVE', 50, 30, 2, 2);

    v_unused := add_attempt(v_peer_one, 100, 'IN_PROGRESS');
    v_unused := add_attempt(v_peer_one, 100, 'FINISHED', 0);
    v_unused := add_attempt(v_peer_two, NULL);
    v_unused := add_attempt(v_peer_two, 100, 'FINISHED', 100, v_other_quiz);
    expect('ABOVE', 50, 30, 2, 2);

    UPDATE attempts SET score_percent = 50, awarded_points = 50 WHERE attempt_id = v_target;
    expect('EQUAL', 50, 0, 2, 2);
    UPDATE attempts SET score_percent = 0, awarded_points = 0 WHERE attempt_id = v_target;
    expect('BELOW', 50, -50, 2, 2);
    UPDATE attempts SET score_percent = 80, awarded_points = 80 WHERE attempt_id = v_target;
    v_unused := add_attempt(v_peer_two, 90);
    expect('ABOVE', 63.33, 16.67, 3, 2);

    UPDATE attempts SET status = 'IN_PROGRESS', finished_at = NULL WHERE attempt_id = v_target;
    expect('IN_PROGRESS', NULL, NULL, 3, 2);
    UPDATE attempts SET status = 'FINISHED', max_points = 0 WHERE attempt_id = v_target;
    expect('NO_SCORE', NULL, NULL, 3, 2);
    UPDATE attempts SET max_points = 100, score_percent = NULL WHERE attempt_id = v_target;
    expect('NO_SCORE', NULL, NULL, 3, 2);
    UPDATE attempts SET score_percent = 80 WHERE attempt_id = v_target;

    pkg_admin.reset_user_quiz_attempts(v_admin, v_peer_one, v_quiz);
    pkg_admin.reset_user_quiz_attempts(v_admin, v_peer_two, v_quiz);
    expect('NO_PEERS', NULL, NULL, 0, 0);

    DBMS_OUTPUT.PUT_LINE('Comparison checks successful: above/below/equal, zero, no peers, filtering, rounding and resets.');
    ROLLBACK TO comparison_test;
EXCEPTION WHEN OTHERS THEN
    ROLLBACK TO comparison_test;
    RAISE;
END;
/
