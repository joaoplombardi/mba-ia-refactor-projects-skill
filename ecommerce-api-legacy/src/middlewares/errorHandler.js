'use strict';

const { AppError } = require('../errors/AppError');
const logger = require('../utils/logger');

/**
 * Single place where errors become HTTP responses.
 *
 * Replaces the per-callback `if (err) return res.status(500).send(...)` blocks,
 * each with its own message, plus the four callbacks that received `err` and
 * silently ignored it.
 */
function notFoundHandler(req, res) {
    res.status(404).send('Rota não encontrada');
}

// Express identifies an error handler by its arity — the `next` parameter is required.
// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, next) {
    if (err instanceof AppError) {
        logger.warn(`${err.name}: ${err.message}`);
        return res.status(err.statusCode).send(err.body);
    }

    // The real cause goes to the server log; the client gets a generic message.
    logger.error('Erro não tratado', err);
    return res.status(500).send('Erro interno');
}

module.exports = { errorHandler, notFoundHandler };
