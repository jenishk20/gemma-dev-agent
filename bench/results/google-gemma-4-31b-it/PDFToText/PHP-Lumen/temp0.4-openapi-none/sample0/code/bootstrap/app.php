<?php

define('LARAVEL_START', microtime(true));

require __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withFacades();
$app->withEloquent();

$app->route/web.php; // This is handled by the router load below

$app->configure('app');

$app->router->group([], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;