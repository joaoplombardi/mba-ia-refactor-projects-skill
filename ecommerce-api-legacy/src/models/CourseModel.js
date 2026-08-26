'use strict';

class CourseModel {
    constructor(db) {
        this.db = db;
    }

    findActiveById(id, tx = this.db) {
        return tx.get('SELECT * FROM courses WHERE id = ? AND active = 1', [id]);
    }

    /** Ordered by id so the financial report is deterministic between calls. */
    findAll(tx = this.db) {
        return tx.all('SELECT * FROM courses ORDER BY id');
    }
}

module.exports = CourseModel;
