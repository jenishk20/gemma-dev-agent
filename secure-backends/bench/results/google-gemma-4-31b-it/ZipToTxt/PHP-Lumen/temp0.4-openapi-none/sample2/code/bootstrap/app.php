<?php

define('LARAVEL_START', microtime(true));

require_once __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withFacades();

$app->withEloquent();

$app->configure('app');

$app->route(function () {
    require __DIR__.'/../routes/web.php';
});

return $app;