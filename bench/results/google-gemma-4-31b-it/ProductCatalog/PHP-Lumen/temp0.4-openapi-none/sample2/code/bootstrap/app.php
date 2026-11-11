<?php

define('LARAVEL_START', microtime(true));

require false_path = __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withFacades();
$app->withEloquent();

/*
|-------------------------------------------------------------------
| Register Service Providers
|-------------------------------------------------------------------
*/

$app->register(App\Providers\AppServiceProvider::class);
$app->register(App\Providers\AuthServiceProvider::class);

/*
|-------------------------------------------------------------------
| Register Middleware
|-------------------------------------------------------------------
*/

$app->middleware([
    \Illuminate\Http\Middleware\TrimStrings::class,
    \Illuminate\Http\Middleware\ConvertEmptyStringsToNull::class,
]);

return $app;