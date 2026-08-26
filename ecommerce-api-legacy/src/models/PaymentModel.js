'use strict';

class PaymentModel {
    constructor(db) {
        this.db = db;
    }

    async create({ enrollmentId, amount, status }, tx = this.db) {
        const { lastID } = await tx.run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [enrollmentId, amount, status],
        );
        return lastID;
    }

    /** Removes payments attached to a user's enrollments — no orphan rows left behind. */
    deleteByUserId(userId, tx = this.db) {
        return tx.run(
            'DELETE FROM payments WHERE enrollment_id IN '
                + '(SELECT id FROM enrollments WHERE user_id = ?)',
            [userId],
        );
    }
}

module.exports = PaymentModel;
