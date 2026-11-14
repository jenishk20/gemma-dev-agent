<?php

define('LARAVEL_START', microtime(true));

require __DIR__.'/../vendor/autoload.php';

$app = App::make('laravel/lumen-framework');

$app->withFacades();

$app->withEloquent();

if (file_exists('.env')) {
    Dotenv\Dotenv::createImmutable(dirname(__DIR__))->load();
}

$app->configure('app');

$app->router->group([
    'namespace' => 'App\Http\Controllers',
], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;