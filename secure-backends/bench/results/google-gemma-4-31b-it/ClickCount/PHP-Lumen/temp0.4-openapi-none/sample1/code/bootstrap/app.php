<?php

define('LARAVEL_LUMEN_APP_NAMESPACE', 'App');
define('LARAVEL_LUMEN_APPLICATION_FOUNDATION_NAMESPACE', 'Illuminate\Foundation');
define('LARAVEL_LUMEN_EXECUTION_FRAMEWORK', 'Illuminate\Execution');

require __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withFacades();
$app->withEloquent();

$app->route/web.php;

// Register the routes
$app->router->group([
    'namespace' => 'App\Http\Controllers',
], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;