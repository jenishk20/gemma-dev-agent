<?php

define('LARAVEL_START', microtime(true));

require __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application;

$app->withFacades();
$app->withEloquent();

$app->route/web.php;

// Load the routes
$app->router->group([], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;