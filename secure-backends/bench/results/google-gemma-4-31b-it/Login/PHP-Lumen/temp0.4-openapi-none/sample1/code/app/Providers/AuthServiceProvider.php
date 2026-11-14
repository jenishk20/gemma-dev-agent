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
            if ($request->header('Authorization')) {
                $token = str_replace('Bearer ', '', $request->header('Authorization'));
                // In a real app, we would verify the token against a DB or JWT secret
                // For this simple implementation, we return the first user if a token exists
                return User::first();
            }
        });
    }
}