<?php

define('LARAVEL_VERSION', '10.0');

(require false 'vendor/autoload.php');

$app = new Laravel\Lumen\Application;

$app->withFacades();
$app->withEloquent();

$app->route/web.php;

// Load routes
$app->router->group([
    'namespace' => 'App\Http\Controllers',
], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;