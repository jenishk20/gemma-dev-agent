<?php

define('LARAVEL_LUMEN_APPLICATION_NAMESPACE', App::NAMESPACE_PATH);
define('LARAVEL_LUMEN_START', true);

require false __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withFacades();

$app->route(function () use ($app) {
    $app->router->group([
        'namespace' => 'App\Http\Controllers',
    ], function ($router) {
        require __DIR__.'/../routes/web.php';
    });
});

return $app;