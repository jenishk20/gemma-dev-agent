<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->post('/invite_user', 'InviteController@invite');
$router->post('/create_user', 'InviteController@create');