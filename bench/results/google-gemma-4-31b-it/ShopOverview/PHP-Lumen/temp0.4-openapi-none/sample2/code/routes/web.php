<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->post('/merchants/register', 'MerchantController@register');
$router->post('/merchants/login', 'MerchantController@login');

$router->group(['middleware' => 'auth'], function () use ($router) {
    $router->post('/merchants/upload-wares', 'MerchantController@uploadWares');
    $router->get('/wares', 'WareController@index');
});