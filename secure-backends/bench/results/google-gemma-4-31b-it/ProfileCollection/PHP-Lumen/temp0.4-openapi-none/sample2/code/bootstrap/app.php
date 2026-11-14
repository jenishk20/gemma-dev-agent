<?php

require_once __DIR__.'/../vendor/autoload.php';

(new Laravel\Lumen\Application(
    dirname(__DIR__)
))->{
    $app = new Laravel\Lumen\Application(dirname(__DIR__));

    $app->withFacades();
    $app->withEloquent();

    $app->configure('database');

    $app->router->group([
        'namespace' => 'App\Http\Controllers',
    ], function ($router) {
        require __DIR__.'/../routes/web.php';
    });

    return $app;
}();