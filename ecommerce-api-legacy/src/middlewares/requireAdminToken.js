'use strict';

const crypto = require('crypto');

const { config } = require('../config');
const { AppError } = require('../errors/AppError');

/**
 * Guard for destructive administrative operations.
 *
 * This project has no identity system, and a refactor is not the place to invent
 * a login flow the audit did not ask for. So the guard uses the same shape as the
 * CLI gate applied to the database reset in the sibling project: a shared operator
 * credential that comes from config and **fails closed** when it is unset.
 *
 * Unset token => the endpoint is disabled (503), never open.
 */
function timingSafeEqualString(a, b) {
    const bufferA = Buffer.from(a);
    const bufferB = Buffer.from(b);
    if (bufferA.length !== bufferB.length) return false;
    return crypto.timingSafeEqual(bufferA, bufferB);
}

module.exports = function requireAdminToken(req, res, next) {
    if (!config.adminApiToken) {
        return next(
            new AppError(
                'Endpoint administrativo desabilitado: defina ADMIN_API_TOKEN.',
                503,
            ),
        );
    }

    const provided = (req.get('authorization') || '').replace(/^Bearer /i, '').trim();
    if (!provided || !timingSafeEqualString(provided, config.adminApiToken)) {
        return next(new AppError('Não autorizado', 401));
    }

    return next();
};
