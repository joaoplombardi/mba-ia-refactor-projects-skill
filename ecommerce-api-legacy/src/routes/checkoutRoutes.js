'use strict';

const express = require('express');

/** HTTP wiring only. Errors are forwarded to the central handler via next(). */
module.exports = function checkoutRoutes(controller) {
    const router = express.Router();

    router.post('/api/checkout', (req, res, next) => {
        controller
            .checkout(req.body)
            .then((result) => res.status(200).json(result))
            .catch(next);
    });

    return router;
};
