<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->get('/recommender', 'RecommenderController@getRecommendations');
$router->post('/recommender', 'RecommenderController@store');