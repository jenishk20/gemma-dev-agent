<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->group(['prefix' => 'api'], function () use ($router) {
    $router->post('/register', 'AuthController@register');
    $router->post('/login', 'AuthController@login');
});

// Redirect root to api for convenience or handle as needed
$router->post('/register', 'AuthController@register');
$router->post('/login', 'AuthController@login');