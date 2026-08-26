'use strict';

const express = require('express');

module.exports = function reportRoutes(controller) {
    const router = express.Router();

    router.get('/api/admin/financial-report', (req, res, next) => {
        controller
            .financialReport()
            .then((report) => res.status(200).json(report))
            .catch(next);
    });

    return router;
};
