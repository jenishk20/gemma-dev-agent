<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->group(['prefix' => 'recommender'], function () use ($router) {
    $router->get('/', 'RecommenderController@index');
    $router->post('/', 'RecommenderController@store');
});