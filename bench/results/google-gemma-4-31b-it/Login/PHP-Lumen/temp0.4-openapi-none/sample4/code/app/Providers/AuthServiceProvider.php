<?php

namespace App\Providers;

use App\Models\User;
use Illuminate\Support\ServiceProvider;

class AuthServiceProvider extends ServiceProvider
{
    public function boot()
    {
        $this->app['auth']->viaRequest('api', function ($request) {
            if ($token = $request->bearerToken()) {
                // In a real app, we would validate the token against a DB or JWT key
                // For this simple implementation, we return the first user if token exists
                return User::first();
            }
        });
    }
}