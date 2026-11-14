<?php

require_once __DIR__.'/../vendor/autoload.php';

(new Laravel\Lumen\Bootstrap\Application(
    dirname(__DIR__)
))->configure('app')
  ->withFacades()
  ->withEloquent()
  ->register(App\Providers\AppServiceProvider::class)
  ->register(App\Providers\AuthServiceProvider::class)
  ->route(
      function ($router) {
          require __DIR__.'/../routes/web.php';
      }
  )
  ->run();