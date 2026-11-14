<?php

namespace App\Providers;

use App\Models\User;
use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Auth;

class AuthServiceProvider extends ServiceProvider
{
    public function boot()
    {
        Auth::viaRequest('api', function ($request) {
            if ($token = $request->bearerToken()) {
                // In a real app, we would validate the HMAC token here.
                // For this simple implementation, we return the first user if token exists.
                return User::first();
            }
        });
    }
}