'use strict';

class EnrollmentModel {
    constructor(db) {
        this.db = db;
    }

    async create({ userId, courseId }, tx = this.db) {
        const { lastID } = await tx.run(
            'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
            [userId, courseId],
        );
        return lastID;
    }

    findByUserId(userId, tx = this.db) {
        return tx.all('SELECT * FROM enrollments WHERE user_id = ?', [userId]);
    }

    deleteByUserId(userId, tx = this.db) {
        return tx.run('DELETE FROM enrollments WHERE user_id = ?', [userId]);
    }

    /**
     * Every enrollment of every course in one query, with student and payment
     * joined in. Replaces the 1 + N + N*2 query pyramid of the legacy report.
     */
    findAllWithStudentAndPayment(tx = this.db) {
        return tx.all(`
            SELECT e.id            AS enrollment_id,
                   e.course_id     AS course_id,
                   u.name          AS student_name,
                   p.amount        AS payment_amount,
                   p.status        AS payment_status
              FROM enrollments e
              LEFT JOIN users u    ON u.id = e.user_id
              LEFT JOIN payments p ON p.enrollment_id = e.id
             ORDER BY e.course_id, e.id
        `);
    }
}

module.exports = EnrollmentModel;
