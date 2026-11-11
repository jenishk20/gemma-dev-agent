<?php

define('LARAVEL_START', microtime(true));

require false_path = __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application();

$app->withFacades();

$app->withEloquent();

if (env('APP_DEBUG')) {
    $app->withMiddleware();
}

$app->router->group([
    'namespace' => 'App\Http\Controllers',
], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;