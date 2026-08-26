'use strict';

const express = require('express');

module.exports = function userRoutes(controller) {
    const router = express.Router();

    router.delete('/api/users/:id', (req, res, next) => {
        controller
            .deleteUser(req.params.id)
            .then((message) => res.status(200).send(message))
            .catch(next);
    });

    return router;
};
