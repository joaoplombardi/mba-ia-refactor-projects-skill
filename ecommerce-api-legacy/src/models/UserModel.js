'use strict';

class UserModel {
    constructor(db) {
        this.db = db;
    }

    findByEmail(email, tx = this.db) {
        return tx.get('SELECT * FROM users WHERE email = ?', [email]);
    }

    findById(id, tx = this.db) {
        return tx.get('SELECT * FROM users WHERE id = ?', [id]);
    }

    findAllByIds(ids, tx = this.db) {
        if (ids.length === 0) return Promise.resolve([]);
        const placeholders = ids.map(() => '?').join(',');
        return tx.all(`SELECT id, name, email FROM users WHERE id IN (${placeholders})`, ids);
    }

    async create({ name, email, passwordHash }, tx = this.db) {
        const { lastID } = await tx.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            [name, email, passwordHash],
        );
        return lastID;
    }

    async deleteById(id, tx = this.db) {
        const { changes } = await tx.run('DELETE FROM users WHERE id = ?', [id]);
        return changes > 0;
    }
}

module.exports = UserModel;
