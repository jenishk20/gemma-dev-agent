<?php

define('LARAVEL_START', microtime(true));

require __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application;

$app->withFacades();
$app->withEloquent();

$app->routeCallback(function () {
});

$app->configure('app');

return $app;