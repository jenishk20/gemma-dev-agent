<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->post('/merchants/register', 'WarehouseController@register');
$router->post('/merchants/login', 'WarehouseController@login');

$router->group(['middleware' => 'auth'], function () use ($router) {
    $router->post('/merchants/upload-wares', 'WarehouseController@uploadWares');
    $router->get('/wares', 'WarehouseController@listWares');
});