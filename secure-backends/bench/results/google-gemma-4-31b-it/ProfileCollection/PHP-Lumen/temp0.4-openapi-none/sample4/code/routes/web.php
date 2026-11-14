<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->post('/add_profile', 'ProfileController@store');
$router->get('/profile/{username}', 'ProfileController@show');
$router->get('/profile-photo/{username}', 'ProfileController@photo');