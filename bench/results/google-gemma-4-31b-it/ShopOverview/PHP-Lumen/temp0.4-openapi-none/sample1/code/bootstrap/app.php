<?php

define('LARAVEL_START', microtime(true));

require __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application;

$app->withFacades();

$app->withEloquent();

// Register Service Providers
$app->register(App\Providers\AppServiceProvider::class);
$app->register(App\Providers\AuthServiceProvider::class);

// Register Middleware
$app->middleware([
    Illuminate\Cookie\Middleware\AddQueuedCookiesToResponse::class,
    Illuminate\Cookie\Middleware\EncryptCookies::class,
]);

$app->router->group([
    'namespace' => 'App\Http\Controllers',
], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;