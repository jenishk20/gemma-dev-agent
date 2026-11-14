<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->group(['prefix' => 'monitor'], function () use ($router) {
    $router->post('commands', 'ProcessController@getProcesses');
});