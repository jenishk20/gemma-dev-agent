<?php

require __DIR__.'/../vendor/autoload.php';

(new Laravel\Lumen\Bootstrap\Application(
    dirname(__DIR__)
))->withFacades()
 ->withEloquent()
 ->configure('app')
 ->routeLoader(function ($app) {
     $app->router->group([], function ($router) {
         require __DIR__.'/../routes/web.php';
     });
 })
 ->create();