<?php

require_once __DIR__ . '/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withFacades();

$app->route(function () use ($app) {
    require __DIR__ . '/../routes/web.php';
});

return $app;