<?php

require_once __DIR__.'/../vendor/autoload.php';

(new Laravel\Lumen\Application(
    dirname(__DIR__)
))->singleton(
    App\Http\Kernel::class,
    function ($app) {
        return new App\Http\Kernel($app);
    }
);

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withBootstrap(Laravel\Lumen\Application::BOOTSTRAP);

// Register routes
$app->router->group([
    'namespace' => 'App\Http\Controllers',
], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;