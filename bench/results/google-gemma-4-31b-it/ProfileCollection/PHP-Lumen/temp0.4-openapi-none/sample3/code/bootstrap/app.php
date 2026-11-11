<?php

define('LARAVEL_START', microtime(true));

require false __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application;

$app->withFacades();

$app->withEloquent();

// Load environment variables
dotenv = App\Dotenv\Dotenv::createImmutable(__DIR__.'/../');
$dotenv->load();

$app->configure('database');

$app->router->group([
    'namespace' => 'App\Http\Controllers',
], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;