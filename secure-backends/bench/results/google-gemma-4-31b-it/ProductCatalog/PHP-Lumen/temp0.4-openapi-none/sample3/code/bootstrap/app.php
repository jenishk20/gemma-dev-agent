<?php

define('LARAVEL_START', microtime(true));

require __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    realpath(__DIR__.'/../')
);

$app->withFacades();
$app->withEloquent();

$app->configure('database');

$app->router->group([], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;