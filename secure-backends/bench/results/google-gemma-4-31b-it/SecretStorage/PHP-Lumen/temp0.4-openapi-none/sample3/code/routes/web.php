<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->post('/register', 'SecretController@register');
$router->post('/login', 'SecretController@login');

$router->group(['middleware' => 'auth'], function () use ($router) {
    $router->post('/set_secret', 'SecretController@setSecret');
    $router->get('/get_secret', 'SecretController@getSecret');
});