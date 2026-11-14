<?php

require_once __DIR__ . '/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withFacades();

$app->withEloquent();

$app->route(function () {
    require __DIR__ . '/../routes/web.php';
});

return $app;