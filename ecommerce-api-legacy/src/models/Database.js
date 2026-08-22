'use strict';

const sqlite3 = require('sqlite3');

/**
 * Promise wrapper around the callback-only sqlite3 driver, plus a transaction
 * boundary.
 *
 * The legacy code nested five levels of callbacks and orchestrated parallel
 * queries with hand-rolled pending counters, which produced a real race: two
 * identical calls to the financial report returned the courses in different
 * orders. Promisifying once lets the controllers read linearly.
 */
class Database {
    constructor(sqliteDb) {
        this.db = sqliteDb;
    }

    static open(file) {
        return new Database(new sqlite3.Database(file));
    }

    get(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
        });
    }

    all(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows || [])));
        });
    }

    /**
     * `lastID` and `changes` live on the callback's `this`, so this one needs a
     * manual wrapper rather than util.promisify.
     */
    run(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.run(sql, params, function runCallback(err) {
                if (err) return reject(err);
                resolve({ lastID: this.lastID, changes: this.changes });
            });
        });
    }

    exec(sql) {
        return new Promise((resolve, reject) => {
            this.db.exec(sql, (err) => (err ? reject(err) : resolve()));
        });
    }

    /**
     * Runs `work` inside BEGIN/COMMIT, rolling back on any rejection.
     * Serialized so a concurrent request cannot interleave into the transaction.
     */
    async transaction(work) {
        return this.#serialize(async () => {
            await this.exec('BEGIN IMMEDIATE');
            try {
                const result = await work(this);
                await this.exec('COMMIT');
                return result;
            } catch (error) {
                await this.exec('ROLLBACK').catch(() => {});
                throw error;
            }
        });
    }

    #queue = Promise.resolve();

    #serialize(task) {
        const run = this.#queue.then(task, task);
        this.#queue = run.then(
            () => undefined,
            () => undefined,
        );
        return run;
    }

    close() {
        return new Promise((resolve, reject) => {
            this.db.close((err) => (err ? reject(err) : resolve()));
        });
    }
}

module.exports = Database;
