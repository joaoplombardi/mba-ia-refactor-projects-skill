'use strict';

class AuditLogModel {
    constructor(db) {
        this.db = db;
    }

    record(action, tx = this.db) {
        return tx.run(
            "INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))",
            [action],
        );
    }
}

module.exports = AuditLogModel;
